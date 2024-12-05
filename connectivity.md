# Environments

There are three types of environments where you can connect Neurorobotics Studio (NRS): **NRS**, **Docker**, and **Local**. These environments are designed to suit your project's specific needs. Among them, **Neurorobotics Studio** is widely recommended for most use cases.

---

## Neurorobotics Studio (NRS)

1. **Magic Link Usage**:  
   The magic link is used by NRS to connect your embodiment to FEAGI. To obtain the magic link:
   - Navigate to the **NRS tab** above the brain visualizer.
   - Click **Embodiment**, then click the **Magic Link** button next to "Custom Connect."

2. **Connect with NRS**:  
   Use the following command to connect:  
   ```
   python controller.py --magic_link "<paste magic link URL here>"
   ```

---

## Local Environment

1. **Connecting to FEAGI Locally**:  
   If FEAGI is running locally on your computer using Python, it connects by default to **localhost** or **127.0.0.1**.

2. **Connect with Local Environment**:  
   - Default connection:  
     ```
     python controller.py
     ```
   - To specify a different IP address, use:  
     ```
     python controller.py --ip <IP_ADDRESS>
     ```
     Replace `<IP_ADDRESS>` with your computer's IP (e.g., `127.0.0.1`).

---

## Docker Environment

### Connecting to Docker or Another Computer

1. **Requirements**:  
   - The IP address of the computer running FEAGI (default: **127.0.0.1**).
   - The port number (default: **8000**).

2. **Connect with Docker**:  
   Use the following command (same as the local setup):  
   ```
   python controller.py
   ```

---

### Setting Up Docker

1. Clone the repository:  
   ```
   git clone git@github.com:feagi/feagi.git
   ```

2. Navigate to the Docker directory:  
   ```
   cd ~/feagi/docker
   ```

3. Pull the required Docker images:  
   ```
   docker compose -f playground.yml pull
   ```

4. Wait for the process to complete.

5. Start the Docker environment:  
   ```
   docker compose -f playground.yml up
   ```

### Notes:
- Ensure that you adjust the IP and port settings as needed for your specific setup.
- For Docker, verify that Docker Compose is installed on your system.

## Open Playground Website:
5. Go to [http://127.0.0.1:4000/](http://127.0.0.1:4000/)
6. Click the "GENOME" button on the top right, next to "API."
7. Click "Essential."


# Extra flags
Example command: `python controller.py --help`
```commandline
optional arguments:
  -h, --help            Show this help message and exit.
  
  -magic_link MAGIC_LINK, --magic_link MAGIC_LINK
                        Use a magic link. You can find your magic link from NRS studio.
                        
  -magic-link MAGIC_LINK, --magic-link MAGIC_LINK
                        Use a magic link. You can find your magic link from NRS studio.
                        
  -magic MAGIC, --magic MAGIC
                        Use a magic link. You can find your magic link from NRS studio.
                        
  -ip IP, --ip IP       Specify the FEAGI IP address.
  
  -port PORT, --port PORT
                        Change the ZMQ port. Use 30000 for Docker and 3000 for localhost.

```