import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
import copy

# --- App Configuration ---
st.set_page_config(
    page_title="Shipyard Delay Simulator (Final Integrated)",
    page_icon="🚢",
    layout="wide"
)

# --- 1. BASELINE PROJECT (EXTENDED AFTER FRIEND'S LAST TASK: T7) ---
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
    {'ID': 'T5', 'Task': '5. Engine Installation (Finland)', 'Duration': 8, 'Category': 'Construction (FIN)', 'Prereq': ['T3B', 'T4']}, # Needs engine AND hull
    {'ID': 'T6', 'Task': '6. Outfitting & Cabins (Finland)', 'Duration': 20, 'Category': 'Outfitting (FIN)', 'Prereq': ['T5']},
    {'ID': 'T7', 'Task': '7. Testing & Sea Trials (Finland)', 'Duration': 10, 'Category': 'Testing (FIN)', 'Prereq': ['T6']},
    
    # --- NEW FINAL STAGE TASKS (Starting at T8 to avoid T7 conflict) ---
    # These tasks now depend on T7, the completion of the original "Testing & Sea Trials"
    {'ID': 'T8', 'Task': '8. Final Systems Check', 'Duration': 3, 'Category': 'Testing & Trials', 'Prereq': ['T7']},
    {'ID': 'T9', 'Task': '9. Final Inspection & Certification', 'Duration': 2, 'Category': 'Certification', 'Prereq': ['T8']},
    {'ID': 'T10', 'Task': '10. Delivery & Final Cleaning', 'Duration': 1, 'Category': 'Delivery', 'Prereq': ['T9']},
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

    # --- NEW DELAY DEFINITIONS (Final Testing & Delivery) ---
    'system_faults_delay': {'name': 'Major System Faults Discovered', 'task_id': ['T8', 'T9', 'T10'], 'weeks': 2}, 
    'bad_weather_delay': {'name': 'Bad Weather (Sea Trials Delay)', 'task_id': 'T7', 'weeks': 2}, # Applies to original T7 task
    'cleaning_delay': {'name': 'Final Cleaning Process Delay', 'task_id': 'T10', 'weeks': 3}, 
}

# --- 3. NEW SIDEBAR (Reflecting new model) ---

st.sidebar.title("🚢 Delay Scenarios")
st.sidebar.write("Select which delay events to simulate based on the 'China -> Germany -> Finland' model.")

with st.sidebar.form(key='delay_form'):
    inputs = {}

    st.sidebar.subheader("1. Planning & Project-Wide")
    inputs['design_flaw'] = st.checkbox('"First-in-Class" Design Flaw (+52 wks)')
    inputs['major_change_order'] = st.checkbox("Major Design Change Order (+8 wks)")
    
    st.sidebar.subheader("2. China Supply Chain (Steel)")
    inputs['china_prod_delay'] = st.checkbox("Steel Mill Production Delay (+4 wks)")
    inputs['china_shipping_delay'] = st.checkbox("China Port Shipping Delay (+3 wks)")

    st.sidebar.subheader("3. Germany Supply Chain (Engine)")
    inputs['germany_prod_delay'] = st.checkbox("Engine Plant Production Delay (+8 wks)")
    inputs['germany_intermediate_delay'] = st.checkbox("German Assembly Bottleneck (+25% time)")
    inputs['germany_shipping_delay'] = st.checkbox("Germany Shipping Delay (+1 wk)")

    st.sidebar.subheader("4. Finland Shipyard (Internal)")
    inputs['finland_crane_failure'] = st.checkbox("Gantry Crane Failure (+3 wks)")
    inputs['finland_labor_shortage'] = st.checkbox("Skilled Labor Shortage (+15% time)")
    inputs['finland_rework'] = st.checkbox("Rework / Quality Failure (+2 wks)")
    
    # --- NEW SIDEBAR SECTION ---
    st.sidebar.subheader("5. Final Testing & Delivery Delays")
    inputs['system_faults_delay'] = st.checkbox("Major System Faults Discovered (+2 wks)")
    inputs['bad_weather_delay'] = st.checkbox("Bad Weather (Sea Trials Delay) (+2 wks)")
    inputs['cleaning_delay'] = st.checkbox("Final Cleaning Process Delay (+3 wks)")

    
    submit_button = st.form_submit_button(label='Run Simulation')

# --- 4. CORE SIMULATION LOGIC (Handles Dependencies) ---

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

# --- 5. VISUAL: SANKEY FLOW DIAGRAM ---
def create_sankey_chart(simulated_plan, baseline_plan):
    """
    Creates a Plotly Sankey diagram to show project flow and delays.
    """
    
    sim_plan_dict = {task['ID']: task for task in simulated_plan}
    base_plan_dict = {task['ID']: task for task in baseline_plan}
    
    # FIX: Shorten labels to prevent visual overlap
    labels = []
    for task in simulated_plan:
        label_text = task['Task'].split('(')[0].strip()
        labels.append(label_text)

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
            
    # Manual X-positions for nodes (EXTENDED)
    sorted_task_ids = [task['ID'] for task in simulated_plan]
    node_x = [0.0] * len(labels) 
    
    x_map = {
        'T1': 0.05, 'T2A': 0.20, 'T3A': 0.30, 'T2B': 0.20, 'T3B': 0.30, 
        'T4': 0.45, 'T5': 0.60, 'T6': 0.70, 'T7': 0.75, 'T8': 0.80, 'T9': 0.90, 'T10': 0.95 # Adjusted positions
    }
    
    for i, task_id in enumerate(sorted_task_ids):
        if task_id in x_map:
            node_x[i] = x_map[task_id]

    # Create the links (edges)
    for task_id, sim_task in sim_plan_dict.items():
        for prereq_id in sim_task['Prereq']:
            if prereq_id in label_map and task_id in label_map:
                sources.append(label_map[prereq_id])
                targets.append(label_map[task_id])
                values.append(sim_plan_dict[prereq_id]['Duration'])

    # Create the Sankey figure
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15, 
            thickness=20, 
            line=dict(color="black", width=0.5),
            label=labels, 
            color=node_colors,
            x=node_x, 
        ),
        link=dict(
            source=sources,
            target=targets,
            value=values
        )
    )],
    layout=dict(
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
        y="Task", 
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

st.title("🚢 Shipyard Domino Effect Simulator (Final Test)")

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
st.write("The top chart is the 'perfect world' plan. The bottom chart shows the cascading impact of your selected delays. Notice how key assembly points must wait for all prerequisites.")

# Create and display the simulated chart
sim_fig = create_gantt_chart(simulated_plan, "Simulated Project Timeline (With Delays)")
sim_fig.update_layout(height=500) # Increased height for more tasks
st.plotly_chart(sim_fig, use_container_width=True)

# Show baseline chart in an expander
with st.expander("Show Baseline Project Timeline (No Delays)"):
    base_fig = create_gantt_chart(baseline_plan, "Baseline Project Timeline (No Delays)")
    base_fig.update_layout(height=500) # Increased height for more tasks
    st.plotly_chart(base_fig, use_container_width=True)

# --- Delay Log ---
st.subheader("Event Log")
if not delay_log:
    st.info("No delays selected. The simulated plan matches the baseline.")
else:
    st.write("The following events were triggered, causing the delays shown above:")
    st.dataframe(pd.DataFrame(delay_log), use_container_width=True)