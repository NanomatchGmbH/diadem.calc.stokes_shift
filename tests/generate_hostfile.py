import subprocess

def get_cpu_count():
    """Get the number of CPUs on the current machine."""
    try:
        # Use nproc command to get the number of CPUs
        cpu_count = subprocess.check_output(['nproc']).strip().decode('utf-8')
        return int(cpu_count)
    except Exception as e:
        print(f"Error getting CPU count: {e}")
        return None

def generate_hostfile(filename, hostname="master"):
    """Generate a hostfile with the specified hostname and number of slots."""
    cpu_count = get_cpu_count()
    if cpu_count is None:
        print("Failed to get the CPU count. Hostfile not generated.")
        return
    
    try:
        with open(filename, 'w') as hostfile:
            hostfile.write(f"{hostname} slots={cpu_count}\n")
        print(f"Hostfile '{filename}' generated successfully with {hostname} slots={cpu_count}.")
    except Exception as e:
        print(f"Error writing hostfile: {e}")

if __name__ == "__main__":
    # Specify the filename for the hostfile
    hostfile_name = "my_hostfile"
    
    # Generate the hostfile
    generate_hostfile(hostfile_name)

