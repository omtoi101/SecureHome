# SecureHome

![Example GIF](media_for_git/example.gif)

**SecureHome is an AI-powered home security camera system that uses facial recognition to identify known individuals and detect intruders.** It provides real-time video streaming, motion and body detection, and sends push notifications to your Discord server.

## Features

- **Motion, Body, and Face Detection:** SecureHome can detect motion, identify human bodies, and recognize known faces.
- **Real-time Video Streaming:** View a live video feed of your camera from any web browser on your local network.
- **Discord Integration:** Receive push notifications with images and video clips of detected events directly to your Discord server.
- **Remote Management via Discord Bot:** Add, remove, and list known faces in the database using simple Discord commands.
- **Text-to-Speech Alerts:** Configure audible alerts to be spoken by the system when events are detected.
- **Automatic Video Recording:** SecureHome automatically records video clips of detected events and saves them to your local disk.
- **IP Camera Support:** Use either a local USB webcam or an IP camera as your video source.
- **Crash Notifications:** Receive a Discord notification if a component of the system crashes.

## Getting Started

The easiest way to get SecureHome up and running is with Docker and `docker-compose`.

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

### Installation

1.  **Clone the repository:**
    ```bash
    git clone -b feature/complete-overhaul https://github.com/omtoi101/SecureHome.git
    cd SecureHome
    ```

2.  **Configure your settings:**
    -   Open the `config.json` file and customize the settings to your liking. See the [Configuration](#configuration) section below for details.
    -   At a minimum, you will need to set your Discord webhook URL and bot token.

3.  **Build and run the application:**
    ```bash
    docker compose up --build
    ```
    This command will build the Docker image and start the application. The web interface will be available at `http://localhost:8040`.

## Configuration

All configuration is done in the `config.json` file.

### `settings`

| Key | Type | Description |
| --- | --- | --- |
| `motion_detection` | boolean | Enable/disable motion detection alerts. |
| `speech` | boolean | Enable/disable text-to-speech alerts. |
| `webserver` | boolean | Enable/disable the web dashboard. |
| `discord_notifications` | boolean | Enable/disable Discord notifications. |
| `discord_bot` | boolean | Enable/disable the Discord bot for face management. |
| `crash_notifications` | boolean | Enable/disable Discord notifications for system crashes. |
| `debug` | boolean | Enable/disable detailed error messages in the logs. |

### `camera`

| Key | Type | Description |
| --- | --- | --- |
| `camera_type` | string | The type of camera to use. Can be `local` or `ip`. |
| `main` | integer | The device index of your local webcam (e.g., 0, 1, 2). Only used if `camera_type` is `local`. |
| `ip_camera_url` | string | The URL of your IP camera's video stream. Only used if `camera_type` is `ip`. |
| `v_cam` | integer | The device index for the virtual camera used for web streaming. |
| `body_inc` | integer | The number of frames a body must be on screen to be recognized. |
| `face_inc` | integer | The number of frames a face must be on screen to be recognized. |
| `motion_inc` | integer | The number of frames motion must be on screen to be recognized. |
| `undetected_time` | integer | The number of frames without detection before the system resets. |
| `fallback_fps` | integer | The frame rate to use if it cannot be automatically detected. |

### `discord`

| Key | Type | Description |
| --- | --- | --- |
| `webhook_url` | string | The URL of your Discord webhook for notifications. |
| `bot_token` | string | The token for your Discord bot. |

## Discord Bot Commands

-   `.addface <name>`: Add a new face to the database. You must attach an image to the message.
-   `.delface <name>`: Delete a face from the database.
-   `.listfaces`: List all the faces in the database.
-   `.help`: Show the list of available commands.

## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
