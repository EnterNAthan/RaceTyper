# Typing Game Frontend

This project is a typing game designed to help players improve their typing skills in a fun and interactive way. The game displays a target phrase that players must type accurately and quickly. The application provides real-time feedback on the player's input, highlighting correct and incorrect characters, and tracking game statistics.

## Project Structure

- **src/**: Contains the source code for the application.
  - **components/**: Reusable components for the game interface.
    - `TypingDisplay.tsx`: Displays the target phrase and manages user input.
    - `ProgressBar.tsx`: Visual representation of the player's typing progress.
    - `GameStats.tsx`: Displays game statistics such as attempts and accuracy.
  - **hooks/**: Custom hooks for managing game logic and keypress events.
    - `useTypingGame.ts`: Manages the game state and logic.
    - `useKeyPress.ts`: Listens for keypress events and updates the game state.
  - **utils/**: Utility functions for typing and validation.
    - `typingHelpers.ts`: Helper functions for calculating accuracy and managing input.
    - `validation.ts`: Functions for validating player input against the target phrase.
  - **types/**: TypeScript types and interfaces for the game.
    - `game.ts`: Defines types related to game state and player statistics.
  - **styles/**: CSS files for styling the application.
    - `globals.css`: Global styles for the application.
    - `components.css`: Component-specific styles.
  - `App.tsx`: Main application component that renders the game.
  - `main.tsx`: Entry point of the application.

- **public/**: Contains static files.
  - `index.html`: Main HTML template for the application.

- `package.json`: Configuration file for npm, listing dependencies and scripts.

- `tsconfig.json`: TypeScript configuration file.

- `vite.config.ts`: Vite configuration file for build options and plugins.

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/typing-game-frontend.git
   cd typing-game-frontend
   ```

2. Install dependencies:
   ```
   npm install
   ```

3. Start the development server:
   ```
   npm run dev
   ```

4. Open your browser and navigate to `http://localhost:3000` to play the game!

## Usage

Once the game is running, you will see a target phrase displayed on the screen. Start typing the phrase in the input field. The application will provide real-time feedback, highlighting correct and incorrect characters. Keep an eye on the progress bar and game statistics to track your performance.

## Contributing

Contributions are welcome! If you have suggestions for improvements or new features, feel free to open an issue or submit a pull request.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.