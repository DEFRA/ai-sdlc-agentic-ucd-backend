---
description: LangGraph memory management
globs: *.py
alwaysApply: false
---
# Memory Management in LangGraph with MongoDB

## Short Term Memory Store using MongoDB Checkpointing

### Overview
This module provides ephemeral, session-based memory storage for LangGraph using MongoDB as the backend for checkpoints. Checkpoints are designed to capture the state of an ongoing conversation and are meant to be short-lived.

### Requirements & Setup
- **MongoDB Connection:** A valid MongoDB URI or an initialized MongoClient instance must be provided.
- **Collection:** Use a dedicated collection (e.g., `langgraph_checkpoints`) for storing checkpoint documents.
- **TTL Indexing:** Optionally set a TTL index on the checkpoint collection to automatically expire documents after a set period.
- **Schema:** Each checkpoint document should minimally contain:
  - A unique checkpoint identifier (`id` or `checkpoint_id`)
  - A timestamp (`ts`)
  - The channel values (e.g., conversation messages)
  - Metadata (e.g., thread or session IDs)

### Operational Rules
1. **Initialization:**
   - Use the MongoDB checkpointer interface (e.g., `MongoDBSaver.from_conn_string(MONGODB_URI)` for short-lived scripts or `MongoDBSaver(mongodb_client)` for persistent applications).
   - Optionally use asynchronous variants (e.g., `AsyncMongoDBSaver.from_conn_string(MONGODB_URI)`).

2. **Saving Checkpoints:**
   - Generate a unique checkpoint ID (e.g., using UUIDs).
   - Store all necessary session data under a consistent schema.
   - Ensure that each checkpoint is associated with a specific session or thread (via a unique thread_id or namespace).

3. **Loading, Updating & Deleting:**
   - **Load:** Retrieve checkpoint data by providing the session configuration.
   - **Update:** Check for existence, then update checkpoint data atomically. Use update operations to modify fields as necessary.
   - **Delete:** Remove checkpoints using a safe delete operation and handle missing checkpoints gracefully.

4. **Session Isolation:**
   - Ensure checkpoints are isolated by session (e.g., using a thread_id in the configuration) to prevent state leakage.

## Long Term Memory Storage using MongoDB

### Overview
This module handles persistent storage for LangGraph where memory needs to persist across sessions. The implementation relies on updating existing MongoDB collections rather than ephemeral checkpointing.

### Requirements & Setup
- **Persistent Connection:** Use a MongoClient or AsyncMongoClient for a long-lived connection.
- **Dedicated Collection:** Use a separate collection (e.g., `langgraph_longterm`) to store persistent memory documents.
- **Schema & Indexing:**
  - Documents should have a defined schema with identifiers (e.g., `memory_id`), timestamps, and memory content.
  - Create indexes on frequently queried fields (e.g., `memory_id`, `session_id`) to enhance performance.
- **Write Strategies:** Utilize upsert operations (i.e., `update_one` with `upsert=True`) for atomic insert/update operations.

### Operational Rules
1. **Initialization:**
   - Connect to the desired MongoDB instance and select the persistent memory collection.
   - Load configuration options (collection name, write concerns, etc.) from environment variables or configuration files.

2. **Insert/Update Operations:**
   - Use upsert operations to either insert new memory or update existing documents.
   - Ensure that concurrent updates are handled gracefully by using appropriate write concerns or transactions if necessary.

3. **Retrieval & Deletion:**
   - Retrieve documents by unique identifiers, session IDs, or other criteria as defined by the application logic.
   - Allow deletion of long term memory documents with proper error handling and confirmation of removal.

4. **Data Integrity & Performance:**
   - Maintain schema consistency across all documents.
   - Use compound indexes when needed for multi-field queries.
   - Consider transaction mechanisms for multi-document operations to ensure data integrity.

## General Guidelines for Code Generation
- **Consistent Naming & Error Handling:** Follow consistent naming conventions and robust error handling patterns.
- **Asynchronous Support:** Where applicable, use asynchronous methods to avoid blocking operations.
- **Configuration Flexibility:** Allow configuration through environment variables or configuration files to set parameters like TTL, collection names, and connection strings.
- **Clear Separation:** Keep the short term and long term memory modules logically separated while using similar design principles to ensure integration with LangGraph projects.
- **Documentation:** Include inline comments and documentation to facilitate maintenance and future updates.
