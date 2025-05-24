# Contributing to Elite Dangerous AI Integration

Thank you for your interest in contributing! Here's how to set up your development environment.

## Prerequisites

*   **Python 3.12**: Make sure you have Python 3.12 installed. You can download it from [python.org](https://www.python.org/downloads/).
*   **Tauri Prerequisites**: Ensure you have all the necessary system dependencies for Tauri development. Follow the guide for your operating system: [Tauri Prerequisites](https://tauri.app/start/prerequisites/).
*   **Node.js**: Required by Tauri, as described in their prerequisites.
*   **Rust**: Required by Tauri, as described in their prerequisites.

## Getting the Code
1. **Fork the repository**: Click the "Fork" button on the top right of the repository page to create your own copy.

2. **Clone your fork**: Use the following command to clone your fork to your local machine:

    ```bash
    git clone your-fork-url
    ```

3. **Navigate to the project directory**:

    ```bash
    cd elite-dangerous-ai-integration
    ```

4. **Add the original repository as a remote** (optional but recommended):

    ```bash
    git remote add upstream official-repo-url
    ```
    
5. **Fetch the latest changes** from the original repository:

    ```bash
    git fetch upstream
    ```
    
6. **Create a new branch** for your changes:

    ```bash
    git checkout -b your-feature-branch
    ```

## Backend Setup (Python)

1. **Install Python 3.12**: 

    Ensure you have at least Python 3.12 installed and available in your PATH. You can check this by running:
    ```bash
    python --version
    ```
    If you see a version number starting with `3.12` or above, you're good to go.

2.  **Create a Virtual Environment:**

    Navigate to the project root directory in your terminal and run:
    ```bash
    python -m venv .venv
    ```
    This creates a virtual environment named `.venv` in the project root.

3.  **Activate the Virtual Environment:**

    *   On **Linux/macOS**:
        ```bash
        source .venv/bin/activate
        ```
    *   On **Windows (Command Prompt)**:
        ```bat
        .venv\Scripts\activate.bat
        ```
    *   On **Windows (PowerShell)**:
        ```powershell
        .venv\Scripts\Activate.ps1
        ```
    You should see `(.venv)` at the beginning of your terminal prompt.

4.  **Install Dependencies:**

    With the virtual environment activated, install the required Python packages:
    ```bash
    pip install -r requirements.txt
    ```

## Frontend Setup (Tauri + UI)

1.  **Navigate to the UI Directory:**

    ```bash
    cd ui
    ```

2.  **Install Node.js Dependencies:**

    ```bash
    npm install
    ```
    This installs the necessary packages for the UI and Tauri development defined in `ui/package.json`.

## Running the Application in Development Mode

1.  **Run the Tauri Development Server:**

    Make sure you are in the `ui` directory and run:
    ```bash
    npm run dev
    ```
    This will build and launch the application with hot-reloading for the frontend. The Python backend is reloaded when stopping the AI Assistant, so start and stop the assistant to see changes.
