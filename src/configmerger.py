import sys
import re
from config_paths import CONFIG_PATH

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
    updated_keys = []
    with open(main_config_file, 'r') as file:
        for line in file:
            if "=" in line and not line.startswith("#"):
                key = line.split('=', 1)[0].strip()
                if key in custom_config:
                    line = f"{key} = {custom_config[key]}\n"
                    updated_keys.append(key)
            updated_lines.append(line)

    # Write the updated lines back to the main config file
    with open(main_config_file, 'w') as file:
        file.writelines(updated_lines)

    # Inform user about the updated keys
    if updated_keys:
        print("The following parameters have been updated:")
        for key in updated_keys:
            print(f"- {key}")
    else:
        print("No parameters were updated.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: configmerger.py <custom_config_file>")
        sys.exit(1)

    main_config_file = CONFIG_PATH
    custom_config_file = sys.argv[1]

    update_config(main_config_file, custom_config_file)
    print(f"Configuration from {custom_config_file} has been merged into {main_config_file}.")

# ---
# # // (old method)
# import sys
# import re

# def update_config(main_config_file, custom_config_file):
#     # Read the custom configuration into a dictionary
#     custom_config = {}
#     with open(custom_config_file, 'r') as file:
#         for line in file:
#             if "=" in line and not line.startswith("#"):
#                 key, value = line.split('=', 1)
#                 custom_config[key.strip()] = value.strip()

#     # Update the main configuration file
#     updated_lines = []
#     with open(main_config_file, 'r') as file:
#         for line in file:
#             if "=" in line and not line.startswith("#"):
#                 key = line.split('=', 1)[0].strip()
#                 if key in custom_config:
#                     line = f"{key} = {custom_config[key]}\n"
#             updated_lines.append(line)

#     # Write the updated lines back to the main config file
#     with open(main_config_file, 'w') as file:
#         file.writelines(updated_lines)

# if __name__ == "__main__":
#     if len(sys.argv) != 3:
#         print("Usage: configmerger.py <main_config_file> <custom_config_file>")
#         sys.exit(1)

#     main_config_file = sys.argv[1]
#     custom_config_file = sys.argv[2]

#     update_config(main_config_file, custom_config_file)
#     print(f"Configuration from {custom_config_file} has been merged into {main_config_file}.")