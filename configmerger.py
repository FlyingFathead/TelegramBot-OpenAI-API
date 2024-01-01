import sys
import re

def update_config(main_config_file, custom_config_file):
    # Read the custom configuration into a dictionary
    custom_config = {}
    with open(custom_config_file, 'r') as file:
        for line in file:
            if "=" in line and not line.startswith("#"):
                key, value = line.split('=', 1)
                custom_config[key.strip()] = value.strip()

    # Update the main configuration file
    updated_lines = []
    with open(main_config_file, 'r') as file:
        for line in file:
            if "=" in line and not line.startswith("#"):
                key = line.split('=', 1)[0].strip()
                if key in custom_config:
                    line = f"{key} = {custom_config[key]}\n"
            updated_lines.append(line)

    # Write the updated lines back to the main config file
    with open(main_config_file, 'w') as file:
        file.writelines(updated_lines)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: configmerger.py <main_config_file> <custom_config_file>")
        sys.exit(1)

    main_config_file = sys.argv[1]
    custom_config_file = sys.argv[2]

    update_config(main_config_file, custom_config_file)
    print(f"Configuration from {custom_config_file} has been merged into {main_config_file}.")