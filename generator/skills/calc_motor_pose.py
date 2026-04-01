# X500 Pose Calculation Skill
# Description: Calculates the rotor positions for a standard Quadrotor X configuration
# Input: arm_length (float)
# Output: JSON object with coordinates for 4 rotors

import sys
import json
import math

# --- Skill Self-Description (For Human Interaction) ---
def get_skill_metadata():
    """
    Returns the parameters this skill needs, for interactive prompts.
    """
    return {
        "name": "Quadrotor Geometry Calculator",
        "description": "Calculates physical coordinates for rotors based on arm length.",
        "parameters": {
            "arm_length": {
                "type": "float",
                "default": 0.25,
                "description": "Length of the arm from center to motor (meters)",
                "required": True
            },
            "z_offset": {
                "type": "float",
                "default": 0.06,
                "description": "Vertical offset of the motor from center (meters)",
                "required": False
            }
        }
    }

def calculate_poses(arm_length=0.25, z_offset=0.06):
    """
    Calculates the X, Y, Z coordinates for a Quad X configuration.
    """
    d = arm_length * 0.70710678
    
    poses = {
        "rotor_0": {"x": d,  "y": -d, "z": z_offset, "dir": "ccw", "desc": "Front Right"},
        "rotor_1": {"x": -d, "y": d,  "z": z_offset, "dir": "ccw", "desc": "Rear Left"},
        "rotor_2": {"x": d,  "y": d,  "z": z_offset, "dir": "cw",  "desc": "Front Left"},
        "rotor_3": {"x": -d, "y": -d, "z": z_offset, "dir": "cw",  "desc": "Rear Right"}
    }
    
    return poses

if __name__ == "__main__":
    # If called with --describe flag, output metadata
    if len(sys.argv) > 1 and sys.argv[1] == "--describe":
        print(json.dumps(get_skill_metadata(), indent=2))
        sys.exit(0)

    try:
        arm_len = float(sys.argv[1]) if len(sys.argv) > 1 else 0.25
        result = calculate_poses(arm_len)
        print(json.dumps(result, indent=2))
    except Exception as e:
        # In a real system, we'd use stderr
        print(json.dumps({"error": str(e)}))
