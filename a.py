import subprocess

def run_command():
    try:
        # Define the command as a list (this is safer and avoids issues with spaces or special characters)
        command = [
            "sudo", 
            "bash", 
            "-c",  # run a shell command
            "cd /etc/pterodactyl && sudo wings configure --panel-url https://panel.vortexcloud.qzz.io --token ptla_sC2oLYmufW2hdqZw7InFVblZrWyuEopbJrUE1KmOGr1 --node 1"
        ]

        # Execute the command
        process = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        # Print the output and error (if any)
        print("Command Output:\n", process.stdout)
        if process.stderr:
            print("Command Errors:\n", process.stderr)

    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}")
        print("Error output:", e.stderr)

if __name__ == "__main__":
    run_command()
