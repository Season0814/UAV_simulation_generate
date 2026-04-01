import os
from universal_sdf_generator import UniversalSDFGenerator

def test_complex_user_input():
    generator = UniversalSDFGenerator()
    
    # 模拟用户非常复杂的自然语言输入
    complex_user_prompt = """
    I want to build a heavy-duty custom quadrotor. 
    Please increase the base link mass to 3.5 kg. 
    Because it's heavier, the inertia should be modified to ixx=0.035, iyy=0.035, izz=0.065. 
    Also, change the base link visual to use a custom red carbon fiber mesh located at 'model://custom_drone_v1/meshes/red_frame.dae'. 
    Make sure the collision geometry uses a cylinder with radius 0.25 and length 0.15.
    Leave the sensors and joints as default.
    """
    
    print("==================================================")
    print("Testing 1: Complex Inertial Generation")
    print("==================================================")
    # 将用户的复杂输入作为 description 传给 LLM，让它去匹配 inertial.sdf.template
    inertial_description = f"User Request: {complex_user_prompt}\nExtract the relevant mass and inertia parameters to generate the inertial component. If not mentioned, use sensible defaults."
    inertial_xml = generator.generate_component(inertial_description, "inertial.sdf.template")
    print("\n[Result - Inertial XML]")
    print(generator.prettify_xml(inertial_xml))
    
    print("\n==================================================")
    print("Testing 2: Complex Visual Generation")
    print("==================================================")
    visual_description = f"User Request: {complex_user_prompt}\nExtract the relevant visual mesh URI and visual properties to generate the visual component. The visual name should be 'base_link_custom_visual'."
    visual_xml = generator.generate_component(visual_description, "visual.sdf.template")
    print("\n[Result - Visual XML]")
    print(generator.prettify_xml(visual_xml))

if __name__ == "__main__":
    test_complex_user_input()
