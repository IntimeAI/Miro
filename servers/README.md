# Miro Server Deployment

This directory contains server deployment scripts and client examples for Miro services.

## Overview

Miro provides two backend services:
- **MiroShape Server**: Image-to-3D model generation service
- **MiroImage Server**: Image editing service powered by Qwen-Image-Edit-2511

## Usage Options

### Option 1: Server-Based Deployment (For API Integration)

Use this option when you need to integrate Miro into your own applications or workflows.

#### Start Both Servers

Use the integrated service management script:

```bash
# Start both servers
./servers/start_servers.sh start --miroimage-gpu 0 --miroshape-gpu 0

# Check server status
./servers/start_servers.sh status

# View logs
./servers/start_servers.sh logs all

# Monitor servers in real-time
./servers/start_servers.sh monitor

# Stop servers
./servers/start_servers.sh stop

# Restart servers
./servers/start_servers.sh restart --miroimage-gpu 0 --miroshape-gpu 0

# Get help
./servers/start_servers.sh help
```

#### Start Individual Servers (Advanced)

If you only need specific functionality:

**MiroImage Server** (Image Editing only):
```bash
bash servers/start_miroimage_server.sh
```

**MiroShape Server** (3D Generation only):
```bash
bash servers/start_miroshape_server.sh
```

### Option 2: API Client Usage

After starting the servers, use the provided client examples to interact with the APIs:

**MiroImage Client** (Image Editing):
```bash
python servers/miroimage_client_example.py
```

**MiroShape Client** (3D Generation):
```bash
python servers/miroshape_client_example.py
```

## API Reference

### MiroShape API

**Endpoint**: `POST http://localhost:8080/generate3d`

**Request Parameters**:
- `image_base64`: Base64-encoded image string
- `image_url`: URL to image (alternative to base64)
- `image_file`: Direct file upload (multipart/form-data)

**Response**: Binary GLB file

### MiroImage API

**Endpoint**: `POST http://localhost:8081/v1/chat/completions`

**Request Format**:
```json
{
  "model": "Qwen-Image-Edit-2511",
  "messages": [
    {
      "role": "user",
      "content": [
        {"type": "text", "text": "Make the background blue"},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
      ]
    }
  ]
}
```

**Response**: JSON with edited images in base64 format

## License

This project is licensed under the MIT License. See the [LICENSE](../LICENSE) file for details.
