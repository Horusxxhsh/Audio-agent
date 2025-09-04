![Alt text](Screenshots/wide.JPG "Audio agent")

# Audio agent

Audio agent is a smart guitar multi-effects processor.

Take a listen to a [sample](https://github.com/pauljonescodes/supertonal/tree/master/Sounds).

It's capabilities, in a rough order:

- A tuner
- Gain staging
- Metering
- Noise gate
- Compression (multiple)
- A "screamer"
- A "mouse drive"
- Equilisation (multiple)
- Multi-stage wave-shaping
- Delay
- Chorus
- Phaser
- Flanger
- Bitcrusher
- Cabinet simulation with IR-loading
- Lo-fi mode
- Limiting

# Work Progress:
1. Added a large language model interaction interface, implementing AI-generated parameter functionality.

![Alt text](Screenshots/chat.png "CHAT UI")

After a successful response, click the reset button to transfer parameters with one click.

2. Added a music memory module, achieving personalized learning.By turning the memory function on/off (MemoryOn/Off), you can decide whether to enable personalized generation.You can simultaneously upload the target song's audio file, which will be stored in the database. This serves as a metric for retrieving similar songs.
   
(Click the SQL button to update the database information. If the memory function is enabled, it will update parameters of similar songs stored in the database based on your preferences.)

# Experiment Preparation:

## Environment Setup:
1. Open supertonal/Source/Components/PythonApplication/PythonApplication.sln with Visual Studio.
2. Add a virtual environment and install the following packages:
   - scikit-learn
   - openai
   - pandas
   - torch
   - librosa
   - transformers

## Environment Variable Configuration:
1. Add the following four items to your system environment variables:
   - SUPERTONAL_PYTHON_INTERPRETER: "C:\path\to\your\python\env\Scripts\python.exe"
   - SUPERTONAL_PYTHON_SCRIPT1: "C:\path\to\your\supertonal\Source\llm.py"
   - SUPERTONAL_PYTHON_SCRIPT2: "C:\path\to\your\supertonal\Source\sql.py"
   - DOCUMENTS_DIR: "C:\path\to\your\Documents"

Note: Please replace the paths with your actual paths.
It is a work in progress, but I've made a strong effort to keep it portable and buildable with basic knowledge of JUCE. To get it working, simply:

```bash
git clone -b master --single-branch --recurse-submodules https://github.com/Horusxxhsh/Audio-agent.git
```

Then you should be able to open up the `.jucer` file and work in your environment of choice.
