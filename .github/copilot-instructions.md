# Audio-agent Copilot Instructions

## Project Overview
Audio-agent is a JUCE-based guitar multi-effects processor integrated with an AI-driven parameter generation system. It combines real-time C++ DSP with Python-based LLM and RAG capabilities.

## Architecture & Data Flow
- **C++ (JUCE)**: Handles the audio engine, UI, and parameter management using `juce::AudioProcessorValueTreeState` (APVTS).
- **Python**: Executes LLM queries (OpenAI/Coze), RAG (ChromaDB/SQLite), and audio feature extraction (librosa/transformers).
- **Integration**: C++ triggers Python scripts via system calls (e.g., `CreateProcessA` on Windows). Data is passed via environment variables and command-line arguments. Results are communicated back through files or database updates.

## Key Files & Directories
- [Source/PluginAudioParameters.h](Source/PluginAudioParameters.h): **CRITICAL**. Contains all parameter IDs and ranges in the `apvts` namespace. Always refer to this for parameter names.
- [Source/PluginAudioProcessor.cpp](Source/PluginAudioProcessor.cpp): The main DSP pipeline.
- [Source/Components/llm.cpp](Source/Components/llm.cpp): The bridge between C++ UI and Python AI logic.
- [Source/llm.py](Source/llm.py): Core Python logic for AI interaction and audio analysis.
- [Source/sql.py](Source/sql.py): Database management and parameter mapping logic.
- [Source/Processors/](Source/Processors/): Individual DSP effect implementations.
- [Experiments/](Experiments/): Contains experiment designs, results analysis, and ablation studies.
- [vector_db/](vector_db/): Storage for the RAG system's vector database.

## Coding Conventions
### C++ (JUCE)
- **Parameters**: Always use IDs defined in `apvts` namespace in [Source/PluginAudioParameters.h](Source/PluginAudioParameters.h).
- **UI**: Follow the modular component pattern in `Source/Components/`. Use `juce::AudioProcessorValueTreeState::SliderAttachment` for linking UI to parameters.
- **Platform**: Note that current process execution logic in `llm.cpp` is Windows-specific (`CreateProcessA`).

### Python
- **Environment**: Relies on environment variables like `SUPERTONAL_PYTHON_INTERPRETER` and `SUPERTONAL_DIR`.
- **Dependencies**: Uses `openai`, `torch`, `librosa`, `transformers`, and `sqlite3`.

## Developer Workflows
- **Build**: Standard JUCE workflow. Use Projucer to generate IDE projects.
- **Environment Setup**: Ensure environment variables from [README.md](README.md) are configured.
- **Database**: Use `sql.py` or the SQL button in the UI to update the music memory database.

## Patterns to Follow
- **Adding a Parameter**: 
  1. Add ID to `apvts` namespace in [Source/PluginAudioParameters.h](Source/PluginAudioParameters.h).
  2. Update `createParameterLayout()` in [Source/PluginAudioProcessor.cpp](Source/PluginAudioProcessor.cpp).
  3. Update `EffectParameters` struct in [Source/Components/llm.h](Source/Components/llm.h) and `extractParameters` in [Source/Components/llm.cpp](Source/Components/llm.cpp) if it should be AI-controllable.
