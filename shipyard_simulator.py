import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
import copy

# --- App Configuration ---
st.set_page_config(
    page_title="Shipyard Delay Simulator",
    page_icon="🚢",
    layout="wide"
)

# --- 1. NEW BASELINE PROJECT (with Dependencies) ---
# We now use a dependency graph. A task can only start after all 'Prereq' tasks are finished.
BASELINE_TASKS = [
    # ID, Task Name, Duration (wks), Category, Prerequisite ID(s)
    {'ID': 'T1', 'Task': '1. Ship Design', 'Duration': 20, 'Category': 'Planning', 'Prereq': []},
    
    # China Supply Chain (Steel)
    {'ID': 'T2A', 'Task': '2A. Steel Production (China)', 'Duration': 15, 'Category': 'Supply Chain (Steel)', 'Prereq': ['T1']},
    {'ID': 'T3A', 'Task': '3A. Steel Shipping (China -> FIN)', 'Duration': 6, 'Category': 'Supply Chain (Steel)', 'Prereq': ['T2A']},

    # Germany Supply Chain (Engine)
    {'ID': 'T2B', 'Task': '2B. Engine Manufacturing (Germany)', 'Duration': 25, 'Category': 'Supply Chain (Engine)', 'Prereq': ['T1']},
    {'ID': 'T3B', 'Task': '3B. Engine Shipping (Germany -> FIN)', 'Duration': 2, 'Category': 'Supply Chain (Engine)', 'Prereq': ['T2B']},
    
    # Finland Shipyard (Assembly)
    {'ID': 'T4', 'Task': '4. Hull Fabrication (Finland)', 'Duration': 20, 'Category': 'Construction (FIN)', 'Prereq': ['T3A']}, # Needs steel
    {'ID': 'T5', 'Task': '5. Engine Installation (Finland)', 'Duration': 8, 'Category': 'Construction (FIN)', 'Prereq': ['T3B', 'T4']}, # DOMINO EFFECT: Needs engine AND hull
    {'ID': 'T6', 'Task': '6. Outfitting & Cabins (Finland)', 'Duration': 20, 'Category': 'Outfitting (FIN)', 'Prereq': ['T5']},
    {'ID': 'T7', 'Task': '7. Testing & Sea Trials (Finland)', 'Duration': 10, 'Category': 'Testing (FIN)', 'Prereq': ['T6']},
]

# --- 2. NEW DELAY DEFINITIONS (Mapped to new Task IDs) ---
DELAY_DEFINITIONS = {
    # China Supply Chain
    'china_prod_delay': {'name': 'Delay at China Steel Mill', 'task_id': 'T2A', 'weeks': 4},
    'china_shipping_delay': {'name': 'Delay Shipping from China (Port Strike)', 'task_id': 'T3A', 'weeks': 3},

    # Germany Supply Chain
    'germany_prod_delay': {'name': 'Delay at German Engine Plant', 'task_id': 'T2B', 'weeks': 8},
    'germany_intermediate_delay': {'name': 'Bottleneck in Germany (Assembly)', 'task_id': 'T2B', 'multiplier': 1.25}, # 25% longer
    'germany_shipping_delay': {'name': 'Delay Shipping from Germany', 'task_id': 'T3B', 'weeks': 1},

    # Finland Shipyard
    'finland_labor_shortage': {'name': 'Skilled Labor Shortage (Finland)', 'task_id': ['T4', 'T5', 'T6'], 'multiplier': 1.15},
    'finland_crane_failure': {'name': 'Gantry Crane Failure (Finland)', 'task_id': 'T4', 'weeks': 3},
    'finland_rework': {'name': 'Rework (Quality Failure)', 'task_id': 'T4', 'weeks': 2},

    # Project-Wide
    'design_flaw': {'name': '"First-in-Class" Design Flaw', 'task_id': 'T1', 'weeks': 52},
    'major_change_order': {'name': 'Major Design Change Order', 'task_id': 'T5', 'weeks': 8}, 
}

# --- 3. NEW SIDEBAR (Reflecting new model) ---

st.sidebar.title("🚢 Delay Scenarios")
st.sidebar.write("Select which delay events to simulate based on the 'China -> Germany -> Finland' model.")

with st.sidebar.form(key='delay_form'):
    inputs = {}

    st.sidebar.subheader("1. China Supply Chain (Steel)")
    inputs['china_prod_delay'] = st.checkbox("Steel Mill Production Delay (+4 wks)")
    inputs['china_shipping_delay'] = st.checkbox("China Port Shipping Delay (+3 wks)")

    st.sidebar.subheader("2. Germany Supply Chain (Engine)")
    inputs['germany_prod_delay'] = st.checkbox("Engine Plant Production Delay (+8 wks)")
    inputs['germany_intermediate_delay'] = st.checkbox("German Assembly Bottleneck (+25% time)")
    inputs['germany_shipping_delay'] = st.checkbox("Germany Shipping Delay (+1 wk)")

    st.sidebar.subheader("3. Finland Shipyard (Internal)")
    inputs['finland_crane_failure'] = st.checkbox("Gantry Crane Failure (+3 wks)")
    inputs['finland_labor_shortage'] = st.checkbox("Skilled Labor Shortage (+15% time)")
    inputs['finland_rework'] = st.checkbox("Rework / Quality Failure (+2 wks)")
    
    st.sidebar.subheader("4. Project-Wide (Planning)")
    inputs['design_flaw'] = st.checkbox('"First-in-Class" Design Flaw (+52 wks)')
    inputs['major_change_order'] = st.checkbox("Major Design Change Order (+8 wks)")
    
    submit_button = st.form_submit_button(label='Run Simulation')

# --- 4. NEW CORE SIMULATION LOGIC (Handles Dependencies) ---

def calculate_simulated_plan(baseline_tasks, delay_inputs):
    """
    Calculates the new project timeline based on selected delays.
    This function now processes tasks based on their prerequisites,
    simulating the "domino effect" (critical path analysis).
    """
    
    tasks_to_process = copy.deepcopy(baseline_tasks)
    completed_tasks = {}  # Stores {task_ID: end_week}
    simulated_plan = []   # The final list of tasks with calculated dates
    delay_log = []
    
    project_start_date = datetime.now().date()

    # Loop until all tasks are processed
    while tasks_to_process:
        processed_a_task = False
        
        # Iterate over remaining tasks
        for i, task in enumerate(tasks_to_process):
            prereqs = task['Prereq']
            
            # Check if all prerequisites are met
            if all(pr_id in completed_tasks for pr_id in prereqs):
                
                # --- This is the "Domino Effect" logic ---
                # A task starts only after its LATEST prerequisite is finished
                if prereqs:
                    start_week = max(completed_tasks[pr_id] for pr_id in prereqs)
                else:
                    start_week = 0  # No prerequisites, start at week 0
                
                task['Start_Wk'] = start_week
                original_duration = task['Duration']
                
                # Apply delays (multipliers and flat weeks)
                task_specific_delay = 0
                task_multiplier = 1.0
                
                for key, active in delay_inputs.items():
                    if active:
                        delay = DELAY_DEFINITIONS[key]
                        task_id = delay['task_id']
                        
                        if (isinstance(task_id, list) and task['ID'] in task_id) or \
                           (isinstance(task_id, str) and task['ID'] == task_id):
                            
                            if 'weeks' in delay:
                                task_specific_delay += delay['weeks']
                                delay_log.append({
                                    'Event': delay['name'],
                                    'Impact': f"+{delay['weeks']} weeks",
                                    'Stage Affected': task['Task']
                                })
                            elif 'multiplier' in delay:
                                task_multiplier *= delay['multiplier']
                                delay_log.append({
                                    'Event': delay['name'],
                                    'Impact': f"x{delay['multiplier']} duration",
                                    'Stage Affected': task['Task']
                                })

                # Calculate new duration and end week
                new_duration = (original_duration * task_multiplier) + task_specific_delay
                task['Duration'] = round(new_duration, 1)
                task['End_Wk'] = task['Start_Wk'] + task['Duration']
                
                # Add friendly dates for the Gantt chart
                task['Start_Date'] = project_start_date + timedelta(weeks=task['Start_Wk'])
                task['End_Date'] = project_start_date + timedelta(weeks=task['End_Wk'])
                
                # Mark task as complete
                completed_tasks[task['ID']] = task['End_Wk']
                simulated_plan.append(task)
                
                # Remove from processing list and mark as processed
                tasks_to_process.pop(i)
                processed_a_task = True
                break # Restart loop since we modified the list

        if not processed_a_task and tasks_to_process:
            # This should not happen if dependencies are correct
            st.error("Error: Circular dependency detected in tasks!")
            break
            
    # Sort the final plan by start week for the Gantt chart
    simulated_plan.sort(key=lambda x: x['Start_Wk'])
    
    # Get total delay
    if simulated_plan:
        total_project_weeks = max(task['End_Wk'] for task in simulated_plan)
    else:
        total_project_weeks = 0

    return simulated_plan, delay_log, total_project_weeks

# --- 5. NEW VISUAL: SANKEY FLOW DIAGRAM ---
def create_sankey_chart(simulated_plan, baseline_plan):
    """
    Creates a Plotly Sankey diagram to show project flow and delays.
    Includes manual x-positioning and SHORTENED LABELS to prevent overlap.
    """
    
    sim_plan_dict = {task['ID']: task for task in simulated_plan}
    base_plan_dict = {task['ID']: task for task in baseline_plan}
    
    # Sankey charts use integer indices for nodes.
    # We need to map our Task IDs (e.g., 'T1') to indices (0, 1, 2...)
    
    # --- FIX: Shorten labels to prevent visual overlap ---
    labels = []
    for task in simulated_plan:
        # e.g., "6. Outfitting & Cabins (Finland)" -> "6. Outfitting & Cabins"
        label_text = task['Task'].split('(')[0].strip()
        labels.append(label_text)
    # --- END FIX ---

    label_map = {task['ID']: i for i, task in enumerate(simulated_plan)}
    
    sources = []
    targets = []
    values = []
    
    # Define colors based on delay
    node_colors = []
    for task_id, sim_task in sim_plan_dict.items():
        base_task = base_plan_dict[task_id]
        if sim_task['End_Wk'] > base_task['End_Wk']:
            node_colors.append('rgba(255, 100, 100, 0.8)') # Red for delayed
        else:
            node_colors.append('rgba(100, 255, 100, 0.8)') # Green for on-time
            
    # --- Manual X-positions for nodes to prevent overlap ---
    # These values (0.0 to 1.0) control the horizontal placement of each node
    
    sorted_task_ids = [task['ID'] for task in simulated_plan]
    node_x = [0.0] * len(labels) # Initialize with dummy values
    
    for i, task_id in enumerate(sorted_task_ids):
        # Map task ID to a horizontal "lane"
        if task_id == 'T1': node_x[i] = 0.05
        elif task_id == 'T2A': node_x[i] = 0.25
        elif task_id == 'T3A': node_x[i] = 0.45
        elif task_id == 'T2B': node_x[i] = 0.25
        elif task_id == 'T3B': node_x[i] = 0.45
        elif task_id == 'T4': node_x[i] = 0.65
        elif task_id == 'T5': node_x[i] = 0.75
        elif task_id == 'T6': node_x[i] = 0.85
        elif task_id == 'T7': node_x[i] = 0.95


    # Create the links (edges)
    for task_id, sim_task in sim_plan_dict.items():
        for prereq_id in sim_task['Prereq']:
            # Ensure both source and target exist in the labels map
            if prereq_id in label_map and task_id in label_map:
                sources.append(label_map[prereq_id])
                targets.append(label_map[task_id])
                # Use the task's duration as the "value" or "flow"
                values.append(sim_plan_dict[prereq_id]['Duration'])

    # Create the Sankey figure
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=20, # Increased padding
            thickness=25, # Increased thickness
            line=dict(color="black", width=0.5),
            label=labels, # Use the new shortened labels
            color=node_colors,
            x=node_x, # Apply the manual x positions
            y=[0.1, 0.0, 0.1, 0.3, 0.4, 0.2, 0.3, 0.2, 0.3] # Add manual y to further separate
        ),
        link=dict(
            source=sources,
            target=targets,
            value=values
        )
    )],
    layout=dict(
        # Set a fixed height to ensure y-coordinates are respected
        height=600 
    ))

    fig.update_layout(
        title_text="Project Flow Diagram (Sankey Diagram)", 
        font_size=12,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
    )
    return fig


def create_gantt_chart(plan_data, title):
    """Creates a Plotly Gantt chart from the plan data."""
    df = pd.DataFrame(plan_data)
    fig = px.timeline(
        df,
        x_start="Start_Date",
        x_end="End_Date",
        y="Task", # Use the full task name here
        color="Category",
        title=title,
        text="Task"
    )
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(
        title_font_size=24,
        font_size=14,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
    )
    return fig

# --- Main Page ---

st.title("🚢 Shipyard Domino Effect Simulator")

# Run a "clean" simulation to get the baseline end week
baseline_plan, _, baseline_end_week = calculate_simulated_plan(BASELINE_TASKS, {})
st.write(f"This tool simulates how different supply chain events can delay a **{baseline_end_week:.0f}-week** shipbuilding project. Use the sidebar to select delays and click 'Run Simulation'.")

# Run simulation with user inputs
simulated_plan, delay_log, simulated_end_week = calculate_simulated_plan(BASELINE_TASKS, inputs)
total_delay = simulated_end_week - baseline_end_week

# --- Display Results ---

st.header("Simulation Results")

# --- Key Metrics ---
col1, col2, col3 = st.columns(3)
col1.metric("Baseline Delivery", f"{baseline_end_week:.1f} Weeks")
col2.metric(
    "Simulated Delivery",
    f"{simulated_end_week:.1f} Weeks",
    delta=f"{total_delay:.1f} Weeks Delay",
    delta_color="inverse"
)
col3.metric("Total Events", f"{len(delay_log)} Active Delays")

st.markdown("---")

# --- NEW: Display Dependency Graph ---
st.subheader("Project Flow Diagram (The Domino Effect)")
st.write("This diagram shows the flow of the project. Tasks turn **red** if they are delayed past their baseline finish week. This lets you trace how a single delay (e.g., in China) flows through the system to the 'Finnish Dock'.")

try:
    sankey_fig = create_sankey_chart(simulated_plan, baseline_plan)
    st.plotly_chart(sankey_fig, use_container_width=True)
except Exception as e:
    st.error(f"An unexpected error occurred while rendering the flow diagram: {e}")

# --- Visual Simulator (Gantt Charts) ---
st.subheader("Visual Simulation: Baseline vs. Simulated Timeline")
st.write("The top chart is the 'perfect world' plan. The bottom chart shows the cascading impact of your selected delays. Notice how '5. Engine Installation' must wait for *both* the hull and the engine to arrive.")

# Create and display the simulated chart
sim_fig = create_gantt_chart(simulated_plan, "Simulated Project Timeline (With Delays)")
sim_fig.update_layout(height=400)
st.plotly_chart(sim_fig, use_container_width=True)

# Show baseline chart in an expander
with st.expander("Show Baseline Project Timeline (No Delays)"):
    base_fig = create_gantt_chart(baseline_plan, "Baseline Project Timeline (No Delays)")
    base_fig.update_layout(height=400)
    st.plotly_chart(base_fig, use_container_width=True)

# --- Delay Log ---
st.subheader("Event Log")
if not delay_log:
    st.info("No delays selected. The simulated plan matches the baseline.")
else:
    st.write("The following events were triggered, causing the delays shown above:")
    st.dataframe(pd.DataFrame(delay_log), use_container_width=True)

