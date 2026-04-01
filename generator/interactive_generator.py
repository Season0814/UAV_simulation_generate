import os
import re
import sys

# Add current directory to path so we can import sdf_generator
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from sdf_generator import SDFGenerator

# ANSI colors for better terminal UI
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}=== {text} ==={Colors.ENDC}")

def print_info(text):
    print(f"{Colors.CYAN}{text}{Colors.ENDC}")

def print_success(text):
    print(f"{Colors.GREEN}{text}{Colors.ENDC}")

def print_warning(text):
    print(f"{Colors.WARNING}{text}{Colors.ENDC}")

def get_user_input(prompt_text):
    try:
        return input(f"{Colors.BLUE}{Colors.BOLD}{prompt_text}{Colors.ENDC} ").strip()
    except EOFError:
        return "exit"

def extract_template_variables(template_content):
    """Extract all ${variable} placeholders from a template string."""
    # Regex to find ${variable}
    matches = re.findall(r'\$\{([a-zA-Z0-9_]+)\}', template_content)
    # Remove duplicates and sort
    return sorted(list(set(matches)))

def main():
    print_header("PX4 Model Generator Assistant")
    print_info("Initializing AI Model... Please wait.")
    
    try:
        generator = SDFGenerator()
    except Exception as e:
        print(f"{Colors.FAIL}Error initializing generator: {e}{Colors.ENDC}")
        return

    print_success("AI Model Ready!")
    print("-" * 60)

    # 1. Analyze Templates to show available parameters
    print_info("Analyzing available templates for customizable parameters...")
    
    try:
        framework_content = generator.load_template_content("model_framework.sdf.template")
        motor_content = generator.load_template_content("motor_model.sdf.template")
        
        framework_vars = extract_template_variables(framework_content)
        motor_vars = extract_template_variables(motor_content)
        
        # Filter out internal variables we handle automatically (like motorPlugins)
        framework_vars = [v for v in framework_vars if v != "motorPlugins"]
        
        print(f"\n{Colors.BOLD}Parameters you can customize:{Colors.ENDC}")
        print(f"  {Colors.BOLD}Model Level:{Colors.ENDC} {', '.join(framework_vars)}")
        print(f"  {Colors.BOLD}Motor Level:{Colors.ENDC} {', '.join(motor_vars)}")
        
    except Exception as e:
        print_warning(f"Could not analyze templates: {e}")
    
    print("-" * 60)
    print_info("You can describe the model you want to build in natural language.")
    print_info("Example: 'Create a quadcopter named my_drone based on x500 with 4 motors.'")
    print_info("         'Motor 0 is front-right ccw, Motor 1 is rear-left ccw...'")
    print_info("Or simply: 'Standard x500 quadcopter'")
    
    while True:
        print("-" * 60)
        user_desc = get_user_input("\nDescribe your model (or type 'exit' to quit):")
        
        if user_desc.lower() in ['exit', 'quit', 'q']:
            print_info("Goodbye!")
            break
            
        if not user_desc:
            continue

        print_info("\nAnalyzing your request...")
        
        try:
            # 2. Extract Model Info first to confirm understanding
            # We use the generator's method to parse the description
            model_info = generator.generate_model_info(user_desc)
            
            current_name = model_info.get("modelName", "custom_model")
            current_base = model_info.get("baseModelURI", "model://x500_base")
            
            print(f"\n{Colors.BOLD}Proposed Configuration:{Colors.ENDC}")
            print(f"  1. Model Name: {Colors.GREEN}{current_name}{Colors.ENDC}")
            print(f"  2. Base Model: {Colors.GREEN}{current_base}{Colors.ENDC}")
            
            action = get_user_input("\nDo you want to modify these parameters? (y/n/generate):")
            
            if action.lower() in ['y', 'yes', 'modify']:
                print_info("Press Enter to keep current value.")
                
                new_name = get_user_input(f"Enter Model Name [{current_name}]:")
                if new_name:
                    current_name = new_name
                    # Update the description to reflect the change so LLM knows context
                    user_desc += f". The model name is {current_name}."
                
                new_base = get_user_input(f"Enter Base Model URI [{current_base}]:")
                if new_base:
                    current_base = new_base
                    user_desc += f". The base model URI is {current_base}."
                    
                print_success("Parameters updated.")
            
            elif action.lower() in ['n', 'no', 'cancel']:
                print_info("Cancelled generation.")
                continue

            # 3. Generate
            print_info(f"\nGenerating model '{current_name}'...")
            
            # Pass the potentially updated description and parameters to the generator
            output_path = generator.run(user_desc, model_name=current_name, base_uri=current_base)
            
            print_success(f"\nModel generated successfully at:\n{output_path}")
            
            # 4. Show preview of the file content (first 20 lines)
            print_info("\nFile Preview (first 20 lines):")
            if os.path.exists(output_path):
                with open(output_path, 'r') as f:
                    lines = f.readlines()
                    preview = "".join(lines[:20])
                    print(f"{Colors.CYAN}{preview}{Colors.ENDC}")
                    if len(lines) > 20:
                        print(f"{Colors.CYAN}... ({len(lines)-20} more lines){Colors.ENDC}")
            
        except KeyboardInterrupt:
            print_info("\nOperation cancelled by user.")
            continue
        except Exception as e:
            print(f"{Colors.FAIL}An error occurred: {e}{Colors.ENDC}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
