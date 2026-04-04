
import sys
import os

# Add the directory containing universal_sdf_generator.py to the python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from universal_sdf_generator import UniversalSDFGenerator

def main():
    generator = UniversalSDFGenerator()
    
    print("\n\n=== Test 1: Standard Sensors Template (Defaults) ===")
    # Description is empty to trigger defaults
    sensor_desc = "Standard sensors for a quadcopter." 
    sensor_xml = generator.generate_component(sensor_desc, "standard_sensors.sdf")
    print(sensor_xml)
    
    print("\n\n=== Test 2: Joint Template (Defaults) ===")
    # Description is empty to trigger defaults
    joint_desc = "A standard rotor joint."
    joint_xml = generator.generate_component(joint_desc, "joint.sdf")
    print(joint_xml)
    
    print("\n\n=== Test 3: Motor Plugin Template (Defaults) ===")
    # Description is empty to trigger defaults
    motor_desc = "A standard motor plugin."
    motor_xml = generator.generate_component(motor_desc, "motor_plugin.sdf")
    print(motor_xml)

    print("\n\n=== Test 4: Motor Plugin Template (Custom Values) ===")
    # Override some defaults
    motor_custom_desc = "Motor number 3, turning clockwise (cw), joint name 'rotor_3_joint', link name 'rotor_3'."
    motor_custom_xml = generator.generate_component(motor_custom_desc, "motor_plugin.sdf")
    print(motor_custom_xml)

if __name__ == "__main__":
    main()
