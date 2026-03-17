## Project Architecture

The project follows a layered backend architecture to maintain separation of concerns and scalability.

### Folder Structure

controllers/
Contains the business logic of the application such as creating, updating, and deleting tasks.

routes/
Defines the API endpoints and maps requests to controller functions.

models/
Defines database schemas and handles interaction with MongoDB.

middleware/
Contains reusable request middleware such as authentication and error handling.

db/
Handles database connection and configuration.

app.js
Main application entry point responsible for initializing the server and registering routes and middleware.

### Request Flow

Client Request
     ↓
Route Handler
     ↓
Controller Logic
     ↓
Database Operation
     ↓
Response Sent to Client