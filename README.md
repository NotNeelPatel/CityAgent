# CityAgent

## Overview
CityAgent is an AI-driven web application developed in collaboration with the City of Ottawa to make municipal asset information easier to access and understand. It provides a secure, natural-language interface where authorized staff can ask plain-language questions and receive grounded answers that include dates, context, and links to official documents. 

Municipal data is often scattered across various internal systems, making it difficult to access efficiently. CityAgent addresses this by centralizing data retrieval, reducing manual workload for city staff, and utilizing AI to accurately summarize and cite infrastructure and asset management information.

## Key Features
* **Natural Language Querying**: Users can ask questions about municipal services, asset conditions, and infrastructure priorities using plain language.
* **Retrieval-Augmented Generation (RAG)**: The system ensures responses are grounded in verified official documents, specifically supporting PDF, XLSX, and CSV file formats.
* **Integrated Document Viewer**: An embedded viewer allows users to explore referenced materials and verify sources directly within the application.
* **Session History**: The application saves users' previous queries and responses, allowing them to easily revisit past searches.
* **Administrative Dashboard**: Authorized personnel can manage the system's knowledge base by uploading new files and deleting outdated documents.

## Technical Architecture

CityAgent follows a modular, layered client-server architecture designed for scalability and maintainability.

### Frontend Layer
* **Framework**: The user interface is built as a Single-Page Application (SPA) using React and Vite. 
* **UI Components**: It utilizes Shadcn to provide clean, accessible, and WCAG-compliant interface components.
* **Authentication**: Secure login is managed via Supabase, supporting email/password and Google Single Sign-On (SSO).

### Backend Layer
* **API & Orchestration**: The backend is developed in Python using FastAPI to handle REST API routing. 
* **Agent Framework**: It leverages the Google Agent Development Kit (ADK) to manage and orchestrate the multi-agent AI workflows.

### Multi-Agent Pipeline
CityAgent utilizes a specialized three-agent pipeline to process user queries accurately:
* **Orchestrator Agent**: Analyzes the user's query, translates intents to keywords, and coordinates the data retrieval process without answering the question directly.
* **Data Analyst Agent**: Specialized in querying and analyzing official PDFs and spreadsheets using RAG. It utilizes dedicated Python tools to filter, extract, and compute data directly from the files.
* **Reasoner Agent**: Synthesizes the final answer based exclusively on the information retrieved by the Data Analyst. It formats the output into a JSON response with clear source citations and handles conversational clarifications.

### Data Storage
The system employs a dual-database architecture managed through Supabase:
* **Relational Database**: A PostgreSQL database stores structured metadata, document attributes, and user session data.
* **Vector Database**: The PGVector extension is used to store high-dimensional text embeddings, enabling semantic similarity searches across uploaded documents.

### AI & Infrastructure
* **LLM Support**: The system is designed to interface with Azure OpenAI for cloud-based inference and Ollama for secure, local open-source model execution.
* **Embedding Models**: Dedicated embedding models process and chunk document data for the RAG pipeline.

## Deployment
CityAgent is built for cloud-first deployment, aligning with enterprise IT infrastructure.
* **Frontend**: Deployed via GitHub Pages for lightweight static hosting.
* **Backend**: Hosted within Docker containers using Azure Container Apps.
* **CI/CD**: Deployment is fully automated using GitHub Actions, ensuring that updates to the main branch are continuously integrated and deployed.

## Setup and Documentation
For full setup instructions, environment variables, database schema configurations, and deployment steps, please refer to the project wikis:

* **Developers Getting Started**: [https://github.com/NotNeelPatel/CityAgent/wiki/Developers-Getting-Started](https://github.com/NotNeelPatel/CityAgent/wiki/Developers-Getting-Started)
* **Users Getting Started & Usage**: [https://github.com/NotNeelPatel/CityAgent/wiki/Users-Getting-Started-and-Usage](https://github.com/NotNeelPatel/CityAgent/wiki/Users-Getting-Started-and-Usage)
* **Main Wiki**: [https://github.com/NotNeelPatel/CityAgent/wiki](https://github.com/NotNeelPatel/CityAgent/wiki)

## Contributors and Acknowledgments

### Main Developers
* **Aashna Verma**: Frontend Development (React/Vite), RAG Vectorization System, and Source Viewer Implementation.
* **Amilesh Nanthakumaran**: Database Architecture, Backend Integration, RAG Vectorization, and Testing Suite Development.
* **Hetarthi Soni**: Frontend UI (Authentication, Dashboard), Backend API Endpoints, and User Session Management.
* **Neel Patel**: System Architecture, Multi-Agent Framework, Infrastructure, and CI/CD Deployment.

### Academic Supervisors
* **Dr. Nafiseh Kahani**: Project Supervisor.
* **Dr. Samuel Ajila**: Second Reader.

### Special Thanks
We would like to extend our thanks to our project partners at the City of Ottawa (Asset Management Team) for their continuous collaboration, project direction, and for providing the necessary datasets to successfully build CityAgent:
* **Kareem Mostafa**
* **Meaghan Wheeler Cuddihy**
