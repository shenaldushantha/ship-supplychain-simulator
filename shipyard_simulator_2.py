import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import networkx as nx
import copy

# --- APP CONFIG ---
st.set_page_config(page_title="Shipyard Pyramid Simulator", layout="wide", page_icon="🏗️")

# --- DATA MODEL: THE AGENTS ---
INITIAL_NODES = {
    # --- LEVEL 1: PROCUREMENT & SUPPLIERS (BASE OF PYRAMID) ---
    'Pur_Weld_Eq': {'label': 'Welding Eq. Supplier', 'duration': 30, 'type': 'Procurement'},
    'Pur_Profiles': {'label': 'Steel Profiles Supplier', 'duration': 30, 'type': 'Procurement'},
    'Pur_Plates': {'label': 'Steel Plates Supplier', 'duration': 30, 'type': 'Procurement'},
    'Pur_Pumps': {'label': 'Pump Supplier', 'duration': 180, 'type': 'Procurement'}, # 6 months
    'Pur_Oil': {'label': 'Oil Supplier', 'duration': 30, 'type': 'Procurement'},
    'Pur_FuelTanks': {'label': 'Fuel Tank Supplier', 'duration': 120, 'type': 'Procurement'}, # 4 months
    'Pur_Engine': {'label': 'Diesel Engine Supplier', 'duration': 240, 'type': 'Procurement'}, # 8 months
    'Pur_Gens': {'label': 'Aux Generator Supplier', 'duration': 300, 'type': 'Procurement'}, # 10 months
    'Pur_Furniture': {'label': 'Furniture Supplier', 'duration': 300, 'type': 'Procurement'}, # 10 months

    # --- LEVEL 2: PREPARATION & SUB-ASSEMBLY ---
    'Steel_Prep': {'label': 'Steel Preparation', 'duration': 120, 'type': 'Construction', 'prereqs': ['Pur_Weld_Eq', 'Pur_Profiles', 'Pur_Plates']},
    'Engine_Prep': {'label': 'Engine Room Prep', 'duration': 21, 'type': 'Outfitting', 'prereqs': ['Pur_Engine']}, # 3 weeks

    # --- LEVEL 3: ASSEMBLY & INSTALLATION ---
    'Panel_Assy': {'label': 'Panel Assembly', 'duration': 180, 'type': 'Construction', 'prereqs': ['Steel_Prep']},
    'Mount_Engine': {'label': 'Mounting Engine', 'duration': 28, 'type': 'Outfitting', 'prereqs': ['Engine_Prep']},
    'Shaft_Install': {'label': 'Shaft Installation', 'duration': 21, 'type': 'Outfitting', 'prereqs': ['Engine_Prep']},
    
    # --- LEVEL 4: BLOCK STAGES ---
    'Block_Assy': {'label': 'Block Assembly', 'duration': 180, 'type': 'Construction', 'prereqs': ['Panel_Assy']},
    'Fuel_Sys': {'label': 'Fuel System Install', 'duration': 28, 'type': 'Outfitting', 'prereqs': ['Pur_Pumps', 'Pur_Oil', 'Pur_FuelTanks']},
    'Aux_Mach': {'label': 'Aux Machinery Install', 'duration': 21, 'type': 'Outfitting', 'prereqs': ['Pur_Gens', 'Shaft_Install']},

    # --- LEVEL 5: INTEGRATION ---
    'Block_Out': {'label': 'Block Outfitting', 'duration': 270, 'type': 'Construction', 'prereqs': ['Block_Assy']},
    'Piping': {'label': 'Piping Installation', 'duration': 28, 'type': 'Outfitting', 'prereqs': ['Mount_Engine', 'Fuel_Sys']}, # 4 weeks
    
    # --- LEVEL 6: ERECTION & CABLING ---
    'Dock_Erect': {'label': 'Dockyard Erection', 'duration': 135, 'type': 'Construction', 'prereqs': ['Block_Out']},
    'Elec_Cable': {'label': 'Electrical Cabling', 'duration': 42, 'type': 'Outfitting', 'prereqs': ['Piping']}, # 6 weeks
    
    # --- LEVEL 7: HULL COMPLETION & VENTILATION ---
    'Hull_Comp': {'label': 'Hull Completion', 'duration': 60, 'type': 'Construction', 'prereqs': ['Dock_Erect']},
    'Ventilation': {'label': 'Ventilation Systems', 'duration': 30, 'type': 'Outfitting', 'prereqs': ['Elec_Cable']},

    # --- LEVEL 8: INSULATION & OUTFITTING ---
    'Outfitting_Hull': {'label': 'General Outfitting', 'duration': 14, 'type': 'Construction', 'prereqs': ['Hull_Comp']},
    'Insulation': {'label': 'Insulation/Fireproofing', 'duration': 30, 'type': 'Outfitting', 'prereqs': ['Ventilation']},

    # --- LEVEL 9: INTERIOR ---
    'Interior_Str': {'label': 'Interior Structure', 'duration': 30, 'type': 'Outfitting', 'prereqs': ['Insulation', 'Pur_Furniture', 'Outfitting_Hull']}, # Merges Hull and Outfitting streams
    
    # --- LEVEL 10: FITTINGS ---
    'Fittings': {'label': 'Fittings & Furniture', 'duration': 28, 'type': 'Outfitting', 'prereqs': ['Interior_Str']},
    
    # --- LEVEL 11: PAINTING ---
    'Painting': {'label': 'Painting', 'duration': 28, 'type': 'Outfitting', 'prereqs': ['Fittings']},

    # --- LEVEL 12: TESTING (START OF FINAL STAGE) ---
    'Stage4_Start': {'label': 'Ready for Testing', 'duration': 0, 'type': 'Milestone', 'prereqs': ['Painting']},
    'Sys_Check': {'label': 'System Check', 'duration': 21, 'type': 'Testing', 'prereqs': ['Stage4_Start']},
    'Final_Clean': {'label': 'Final Cleaning', 'duration': 30, 'type': 'Testing', 'prereqs': ['Stage4_Start']},

    # --- LEVEL 13: TRIALS ---
    'Harbour_Trials': {'label': 'Harbour Trials', 'duration': 14, 'type': 'Testing', 'prereqs': ['Sys_Check', 'Final_Clean']}, # 2 weeks (implied)
    
    # --- LEVEL 14: SEA TRIALS ---
    'Sea_Trials': {'label': 'Sea Trials', 'duration': 14, 'type': 'Testing', 'prereqs': ['Harbour_Trials']},
    
    # --- LEVEL 15: PERFORMANCE ---
    'Perf_Test': {'label': 'Performance Testing', 'duration': 14, 'type': 'Testing', 'prereqs': ['Sea_Trials']},
    
    # --- LEVEL 16: CERTIFICATION ---
    'Cert': {'label': 'Certification', 'duration': 14, 'type': 'Testing', 'prereqs': ['Perf_Test']},
    
    # --- LEVEL 17: INSPECTION ---
    'Final_Insp': {'label': 'Final Inspection', 'duration': 5, 'type': 'Testing', 'prereqs': ['Cert']},
    
    # --- LEVEL 18: DELIVERY (PEAK OF PYRAMID) ---
    'Delivery': {'label': '🚢 DELIVERY', 'duration': 5, 'type': 'Delivery', 'prereqs': ['Final_Insp']},
}

# --- HELPER FUNCTIONS ---

def calculate_schedule(nodes_data):
    """
    Topological sort calculation to determine start/end dates for all agents.
    """
    for node_id in nodes_data:
        nodes_data[node_id]['start_day'] = 0
        nodes_data[node_id]['end_day'] = 0
    
    changed = True
    while changed:
        changed = False
        for node_id, node in nodes_data.items():
            max_prereq_end = 0
            if 'prereqs' in node:
                for prereq in node['prereqs']:
                    if nodes_data[prereq]['end_day'] > max_prereq_end:
                        max_prereq_end = nodes_data[prereq]['end_day']
            
            if node['start_day'] != max_prereq_end:
                node['start_day'] = max_prereq_end
                changed = True
            
            new_end = node['start_day'] + node['duration'] + node.get('delay', 0)
            if node['end_day'] != new_end:
                node['end_day'] = new_end
                changed = True
                
    return nodes_data

def get_pyramid_layout(nodes_data):
    """
    Calculates X, Y coordinates to enforce a Pyramid shape.
    """
    G = nx.DiGraph()
    for node_id, node in nodes_data.items():
        G.add_node(node_id)
        if 'prereqs' in node:
            for pr in node['prereqs']:
                G.add_edge(pr, node_id)
    
    levels = {}
    max_level = 0
    for node in G.nodes():
        try:
            length = nx.shortest_path_length(G, source=node, target='Delivery')
            levels[node] = length
            if length > max_level:
                max_level = length
        except nx.NetworkXNoPath:
             levels[node] = 0

    nodes_by_level = {}
    for node, level in levels.items():
        if level not in nodes_by_level:
            nodes_by_level[level] = []
        nodes_by_level[level].append(node)
        
    pos = {}
    for level, level_nodes in nodes_by_level.items():
        level_nodes.sort() 
        count = len(level_nodes)
        y = max_level - level
        for i, node_id in enumerate(level_nodes):
            x = i - (count - 1) / 2
            x *= 2.0 
            pos[node_id] = (x, y)
            
    return pos

# --- STATE MANAGEMENT ---

if 'nodes' not in st.session_state:
    st.session_state['nodes'] = copy.deepcopy(INITIAL_NODES)

# Default selection if none exists
if 'selected_agent_id' not in st.session_state:
    st.session_state['selected_agent_id'] = 'Delivery'

# --- MAIN CALCULATION (Run BEFORE Sidebar) ---

calculated_nodes = calculate_schedule(st.session_state['nodes'])
baseline_nodes = calculate_schedule(copy.deepcopy(INITIAL_NODES))

total_duration = calculated_nodes['Delivery']['end_day']
baseline_duration = baseline_nodes['Delivery']['end_day']
total_delay = total_duration - baseline_duration

# --- LAYOUT CALCULATION ---
pos = get_pyramid_layout(calculated_nodes)

# Create Plotly traces
edge_x = []
edge_y = []
for node_id, node in calculated_nodes.items():
    if 'prereqs' in node:
        for pr in node['prereqs']:
            x0, y0 = pos[pr]
            x1, y1 = pos[node_id]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])

# Node data preparation for Plotly
ordered_node_ids = list(pos.keys()) # Keep order for click mapping
node_x = []
node_y = []
node_text = []
node_color = []
node_size = []

for node_id in ordered_node_ids:
    x, y = pos[node_id]
    node = calculated_nodes[node_id]
    
    base_end_day = baseline_nodes[node_id]['end_day']
    actual_end_day = node['end_day']
    
    is_delayed_impact = actual_end_day > base_end_day
    added_delay = node.get('delay', 0)
    
    node_x.append(x)
    node_y.append(y)
    
    info = (f"<b>{node['label']}</b><br>"
            f"End: Day {actual_end_day} (Plan: {base_end_day})<br>"
            f"Direct Delay Added: {added_delay} days")
    node_text.append(info)
    
    # Color logic
    if node_id == st.session_state['selected_agent_id']:
        node_color.append('#FFFF00') # Yellow for selected
        node_size.append(30) # Bigger for selected
    elif is_delayed_impact:
        node_color.append('#FF4B4B') # Red for delayed
        node_size.append(20)
    elif node['type'] == 'Delivery':
        node_color.append('#00FF00') # Green for Delivery
        node_size.append(30)
    elif node['type'] == 'Procurement':
        node_color.append('#1f77b4') # Blue for Procurement
        node_size.append(15)
    else:
        node_color.append('#DDDDDD') # Grey for others
        node_size.append(15)

# Draw Figure
fig = go.Figure()

# Edges (Lines)
fig.add_trace(go.Scatter(
    x=edge_x, y=edge_y,
    line=dict(width=1, color='#888'),
    hoverinfo='none',
    mode='lines'
))

# Nodes (Dots)
fig.add_trace(go.Scatter(
    x=node_x, y=node_y,
    mode='markers+text',
    text=[calculated_nodes[nid]['label'] for nid in ordered_node_ids],
    textposition="top center",
    hoverinfo='text',
    hovertext=node_text,
    marker=dict(
        showscale=False,
        color=node_color,
        size=node_size,
        line_width=2
    )
))

fig.update_layout(
    title="Construction Pyramid (Click a node to Edit)",
    showlegend=False,
    hovermode='closest',
    margin=dict(b=0,l=0,r=0,t=40),
    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
    height=700,
    plot_bgcolor='rgba(0,0,0,0)',
    clickmode='event+select' # Enable clicking
)

# --- DASHBOARD HEADER ---

st.title("🏗️ Construction Pyramid Simulator")
st.markdown("""
**Instructions:** Click on any node in the pyramid below to open its settings in the sidebar.
""")

m1, m2, m3 = st.columns(3)
m1.metric("Project Delivery", f"Day {total_duration}", delta=f"{total_delay} Days Delay", delta_color="inverse")
m2.metric("Baseline Target", f"Day {baseline_duration}")
m3.metric("Critical Path Agent", f"{st.session_state['nodes'][st.session_state['selected_agent_id']]['label']}")

# --- VISUALIZATION RENDER ---

# Render Chart and Capture Click Events
event = st.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode="points")

# Handle Click Event
if event and event['selection']['points']:
    # Get the index of the clicked point from the event data
    clicked_point_index = event['selection']['points'][0]['point_index']
    # Map index back to Node ID using the ordered list we used for plotting
    clicked_node_id = ordered_node_ids[clicked_point_index]
    
    # Update Session State if different
    if clicked_node_id != st.session_state['selected_agent_id']:
        st.session_state['selected_agent_id'] = clicked_node_id
        st.rerun()

# --- SIDEBAR: AGENT EDITOR ---

st.sidebar.title("🛠️ Agent Editor")

if st.sidebar.button("⚠️ Reset All Agents"):
    st.session_state['nodes'] = copy.deepcopy(INITIAL_NODES)
    st.rerun()

st.sidebar.markdown("### Selected Agent")

# Get the currently selected agent from state
selected_id = st.session_state['selected_agent_id']
agent = st.session_state['nodes'][selected_id]

# Show details
st.sidebar.info(f"**Editing:** {agent['label']}")
st.sidebar.write(f"**Type:** {agent['type']}")
st.sidebar.write(f"**Baseline Duration:** {INITIAL_NODES[selected_id]['duration']} days")

# Input: Custom Delay
current_delay = agent.get('delay', 0)
new_delay = st.sidebar.number_input(
    "Added Delay (Days)", 
    value=current_delay, 
    step=1, 
    key=f"delay_input_{selected_id}", # Unique key ensures input refreshes when node changes
    help="Add days to simulate strikes, shortages, or rework."
)

# Input: Quick Risk Triggers
st.sidebar.markdown("##### ⚠️ Trigger Risk Scenarios")
col_r1, col_r2 = st.sidebar.columns(2)

if col_r1.button("Stock Out", key=f"btn_stock_{selected_id}"):
    new_delay += 14
    st.toast(f"{agent['label']}: Stock Out (+14 days)")
    
if col_r2.button("Mat. Reject", key=f"btn_reject_{selected_id}"):
    new_delay += 42
    st.toast(f"{agent['label']}: Quality Rejection (+42 days)")

if st.sidebar.button("Major Engine Delay (2mo)", key=f"btn_eng_{selected_id}"):
    new_delay += 60
    st.toast("Major Engine Delay (+60 days)")

# Update State if delay changed
if new_delay != current_delay:
    st.session_state['nodes'][selected_id]['delay'] = new_delay
    st.rerun()

# Reset Agent Button
if st.sidebar.button("Reset Agent", key=f"btn_reset_{selected_id}"):
    st.session_state['nodes'][selected_id]['delay'] = 0
    st.rerun()

# --- DETAILED DATA VIEW ---
with st.expander("📊 View Detailed Data Table"):
    df_nodes = pd.DataFrame.from_dict(calculated_nodes, orient='index')
    if 'delay' not in df_nodes.columns:
        df_nodes['delay'] = 0
    df_nodes = df_nodes[['label', 'type', 'duration', 'delay', 'start_day', 'end_day']]
    df_nodes = df_nodes.sort_values(by='end_day')
    st.dataframe(df_nodes, use_container_width=True)