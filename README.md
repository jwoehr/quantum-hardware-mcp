# Quantum Hardware MCP Server

An open-source MCP server that gives AI assistants live access to real quantum computers  IBM Quantum and IonQ. Ask natural questions, submit circuits, compare hardware, and get results. No dashboard. No manual API calls.

Built with [FastMCP](https://github.com/jlowin/fastmcp), [qiskit-ibm-runtime](https://github.com/Qiskit/qiskit-ibm-runtime), and [qiskit-ionq](https://github.com/Qiskit-Partners/qiskit-ionq).

Collaboration: [Jack Woehr](https://github.com/jwoehr)  IBM Quantum veteran, Qiskit contributor.

---

## What this is

Quantum researchers spend hours on things that should take seconds:
- Checking which device has the shortest queue
- Finding the lowest error rate before submitting a circuit
- Submitting to IBM, then repeating the same process on IonQ separately
- Waiting for results, then pulling them manually

This server gives your AI assistant a direct line to both IBM and IonQ hardware. You ask once. It handles both.

---

## How it works

When you ask a question, here is the path it takes:

```
You (chat.js)
    ↓ sends your question to
Dispatcher (agent-server.js)
    ↓ asks the LLM: "is this IBM or IonQ?"
    ↓ routes to the right expert
    ├── IBM Subagent (ibm-subagent.js)
    │       ↓ connects to
    │   MCP Server (server.py)
    │       ↓ calls IBM Quantum API → returns real data
    │
    └── IonQ Subagent (ionq-subagent.js)
            ↓ connects to
        MCP Server (server.py)
            ↓ calls IonQ API → returns real data
```

Each subagent is an expert for its platform  IBM subagent only sees IBM tools, IonQ subagent only sees IonQ tools. The dispatcher routes automatically based on your question.

---

## What each file does

| File | Job |
|------|-----|
| `server.py` | The only file that touches real quantum hardware. All IBM + IonQ tools live here. |
| `agent/agent-server.js` | The brain. Reads your question, classifies IBM or IonQ, spawns the right expert. |
| `agent/chat.js` | Your terminal interface. Where you type questions and see answers. |
| `agent/subagents/ibm-subagent.js` | IBM expert. Only knows IBM tools. |
| `agent/subagents/ionq-subagent.js` | IonQ expert. Only knows IonQ tools. |
| `agent/subagents/base-subagent.js` | Shared ReAct loop logic used by both subagents. |
| `snapshot.py` | Runs every 6 hours. Records device stats to `devices.db` and `data/snapshots.csv`. |
| `tests/test_dispatcher.py` | 9 hard tests covering routing accuracy, tool isolation, and end-to-end job submission. |

---

## Tools exposed

### IBM Quantum tools

| Tool | What it does |
|------|-------------|
| `list_devices` | All IBM quantum computers you can access + live status |
| `get_device_details` | Deep info on one machine: error rates, T1/T2, queue depth |
| `compare_devices` | Rank machines by CX error, queue depth, qubit count, or combined score |
| `queue_status` | Current queue snapshot — pick the shortest wait |
| `best_qubits` | Best n qubits on a machine right now, scored by calibration data |
| `device_history` | Snapshots for one machine over the last N days |
| `device_on_date` | Historical stats for any past date (for reproducibility in papers) |
| `submit_job` | Compile and submit an OpenQASM 2.0 or 3.0 circuit — returns a `job_id` |
| `job_status` | Check status: QUEUED / RUNNING / DONE / ERROR |
| `job_results` | Retrieve bit-string measurement counts from a completed job |
| `cancel_job` | Cancel a queued or running job |
| `list_jobs` | Your most recent jobs with status and backend |
| `run_grover` | Built-in Grover's search — builds the full circuit, picks the least-busy backend, submits |
| `estimate_expectation` | Estimator primitive — computes ⟨ψ\|O\|ψ⟩ for Pauli observables (VQE, QAOA, quantum chemistry) |
| `circuit_report` | Dry-run: transpiles your circuit and returns gate counts, qubit mapping, per-pair CX errors, estimated fidelity. No queue. |
| `debug_circuit` | Pre-flight check — finds missing measurements, decoherence violations, qubit mismatches before you waste queue time. |

### IonQ tools

| Tool | What it does |
|------|-------------|
| `ionq_devices` | List all IonQ quantum computers and simulators |
| `ionq_submit_job` | Submit an OpenQASM 2.0 circuit to IonQ hardware or simulator |
| `ionq_job_status` | Check IonQ job status |
| `ionq_job_results` | Retrieve measurement counts from a completed IonQ job |

---

## Real experiment: Pascal's Triangle on quantum hardware

We used this tool to run the same circuit on both IBM and IonQ and compare the noise.

**The circuit:** encode C(6,3) = 20 as the binary state `|10100⟩`, run 1000 shots, measure.

| | IBM ibm_kingston (real hardware) | IonQ (simulator) |
|---|---|---|
| Correct answer `10100` | 942/1000 — **94.2%** | 1000/1000 — **100%** |
| Noise | 5.8% (readout errors) | 0% (noiseless simulator) |

The 5.8% error on IBM is typical for current superconducting hardware. Next step: run on IonQ real hardware for a true apples-to-apples noise comparison.

This is the beginning of a systematic study of Singmaster's Conjecture — searching Pascal's Triangle for numbers appearing 9+ times, using quantum hardware to probe larger search spaces than classical exhaustion.

---

## Chat commands

| Command | What it does |
|---------|-------------|
| `/poll IBM <job_id> [interval]` | Poll an IBM job every N seconds until done, auto-stops on completion |
| `/poll IonQ <job_id> [interval]` | Same for IonQ jobs |
| `/save @/path/to/file` | Save your chat history to a Markdown file |
| `/nolocal` | Toggle bypass of the local Qiskit code model (granite/mistral) — useful when Ollama is slow or unavailable |
| `/clear` | Clear chat history |
| `/help` | Show all commands |
| `/exit` or `/quit` | End the session |

---

## IBM account configuration

Beyond the token, IBM Quantum supports multiple accounts and instances. Configure in `.env`:

```bash
# Pin a specific hub/group/project (leave unset for IBM auto-select)
IBM_INSTANCE=ibm-q/open/main

# Platform: ibm_quantum_platform (default) or ibm_cloud
IBM_CHANNEL=ibm_quantum_platform

# Set false to hide account info from the server startup banner
IBM_SHOW_ACCOUNT_INFO=true
```

---

## Prerequisites

- Python 3.10+
- Node.js 18+
- An IBM Quantum account (free) — [quantum.ibm.com](https://quantum.ibm.com)
- An IonQ account (optional) — [cloud.ionq.com](https://cloud.ionq.com)
- An LLM API key (Anthropic, Gemini, OpenAI, or local Ollama)

---

## Quick start

### 1. Clone and install

```bash
git clone https://github.com/Lokesh-2025/quantum-hardware-mcp.git
cd quantum-hardware-mcp
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cd agent && npm install && cd ..
```

### 2. Configure

```bash
cp .env.example .env
```

Edit `.env` — add your IBM token and LLM key. IonQ key is optional.

> `.env` is in `.gitignore` — it will never be committed.

### 3. Run with Docker (recommended)

```bash
docker compose up --build
```

Then in a separate terminal:

```bash
node agent/chat.js
```

### 4. Or run manually

Terminal 1 — MCP server:
```bash
source .venv/bin/activate
python3 server.py --transport http
```

Terminal 2 — agent:
```bash
cd agent && node agent-server.js
```

Terminal 3 — chat:
```bash
cd agent && node chat.js
```

---

## LLM provider support

Not locked into any provider:

| Provider | Cost | Config |
|----------|------|--------|
| Anthropic (Claude) | Paid | `LLM_PROVIDER=anthropic` + `ANTHROPIC_API_KEY` |
| Google Gemini | Free tier | `LLM_PROVIDER=gemini` + `GEMINI_API_KEY` |
| Ollama | Free, local | `LLM_PROVIDER=ollama` + `OLLAMA_MODEL` |
| OpenAI | Paid | `LLM_PROVIDER=openai` + `OPENAI_API_KEY` |
| vLLM | Self-hosted | `LLM_PROVIDER=vllm` + `VLLM_BASE_URL` |

> **Privacy note:** For sensitive research — pharmaceutical, government, or unpublished academic work — run fully offline with Ollama. Zero data leaves your machine. The LLM runs locally, and the MCP server only contacts IBM/IonQ when you explicitly submit a job.

---

## Connect to Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "quantum-hardware": {
      "command": "/absolute/path/to/.venv/bin/python",
      "args": ["/absolute/path/to/quantum-hardware-mcp/server.py"]
    }
  }
}
```

Restart Claude Desktop. The hammer icon will show all quantum tools.

---

## Automatic snapshots

`snapshot.py` records device stats every 6 hours:
- **Locally** — writes to `devices.db`, feeds `device_history` and `device_on_date`
- **GitHub Actions** — appends to `data/snapshots.csv` every 6 hours, building a public historical record

If a reviewer asks "what was the CX error on the day you ran Figure 3?" — you can answer exactly.

---

## Project structure

```
quantum-hardware-mcp/
├── server.py                    # MCP server — all IBM + IonQ tools
├── snapshot.py                  # Background device snapshot agent
├── report.py                    # Daily fleet report (runs at 8am)
├── requirements.txt
├── .env.example
├── docker-compose.yml
├── Dockerfile
├── agent/
│   ├── agent-server.js          # Dispatcher — routes IBM vs IonQ
│   ├── chat.js                  # Terminal chat interface
│   ├── Dockerfile
│   ├── subagents/
│   │   ├── base-subagent.js     # Shared ReAct loop logic
│   │   ├── ibm-subagent.js      # IBM specialist
│   │   └── ionq-subagent.js     # IonQ specialist
│   └── .env.example
├── tests/
│   └── test_dispatcher.py       # 9 dispatcher tests (routing, isolation, E2E)
├── data/
│   └── snapshots.csv            # Historical device data (public, updated by CI)
└── .github/workflows/
    └── snapshot.yml             # GitHub Actions: snapshot every 6h
```

---

## Roadmap

- [x] IBM Quantum tools (list, compare, submit, results)
- [x] IonQ support
- [x] Subordinate agent architecture (dispatcher → IBM/IonQ experts)
- [x] Job polling (`/poll`), chat saving (`/save`), local model bypass (`/nolocal`)
- [x] IBM multi-account config (instance, channel)
- [x] Starlette SSE compatibility fix (works with all Starlette versions)
- [ ] Pascal's Triangle / Singmaster's Conjecture experiment (IBM vs IonQ real hardware)
- [ ] `/load` — reload a saved chat session
- [ ] Publish to MCP registries
- [ ] Daily autonomous report agent

---

## License

MIT — see [LICENSE](LICENSE).
