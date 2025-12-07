"""
final_simulater_test.py
Simple backend tester for the Shipyard Pyramid Simulator.
This script verifies delay propagation, dependency order,
and correct calculation of start/end days.

This is a standalone test (no Streamlit).
"""

from copy import deepcopy

# ---- IMPORT NODES FROM FRIEND'S CODE ----
from shipyard_simulator_2 import INITIAL_NODES, calculate_schedule


def print_agent_info(nodes, agent_id):
    agent = nodes[agent_id]
    print(f"\n=== {agent['label']} ===")
    print(f"Type: {agent['type']}")
    print(f"Start Day: {agent['start_day']}")
    print(f"End Day: {agent['end_day']}")
    print(f"Delay Added: {agent.get('delay', 0)}")


def test_final_stage():
    print("\n----- TEST 1: FINAL STAGE TIMELINE -----")

    nodes = deepcopy(INITIAL_NODES)
    nodes = calculate_schedule(nodes)

    for stage in ["Stage4_Start", "Sys_Check", "Final_Clean", "Harbour_Trials", "Sea_Trials", "Perf_Test", "Cert", "Final_Insp", "Delivery"]:
        print_agent_info(nodes, stage)


def test_delay_propagation():
    print("\n----- TEST 2: DELAY PROPAGATION -----")

    nodes = deepcopy(INITIAL_NODES)

    # Add a delay to one agent
    nodes["Engine_Prep"]["delay"] = 10
    print("\nAdded 10-day delay to Engine Preparation")

    # Recalculate schedule
    nodes = calculate_schedule(nodes)

    # Print impact on dependent tasks
    for stage in ["Engine_Prep", "Mount_Engine", "Shaft_Install", "Piping", "Elec_Cable"]:
        print_agent_info(nodes, stage)


def test_critical_delivery():
    print("\n----- TEST 3: DELIVERY DATE TEST -----")

    baseline = calculate_schedule(deepcopy(INITIAL_NODES))
    baseline_delivery = baseline["Delivery"]["end_day"]

    print(f"\nBaseline Delivery Day: {baseline_delivery}")

    # Add big delay
    nodes = deepcopy(INITIAL_NODES)
    nodes["Fuel_Sys"]["delay"] = 30
    nodes = calculate_schedule(nodes)

    new_delivery = nodes["Delivery"]["end_day"]
    print(f"New Delivery Day: {new_delivery}")
    print(f"Total Delay Impact: {new_delivery - baseline_delivery} days")


if __name__ == "__main__":
    print("### FINAL SIMULATOR BACKEND TEST ###")

    test_final_stage()
    test_delay_propagation()
    test_critical_delivery()

    print("\nAll tests completed.")
