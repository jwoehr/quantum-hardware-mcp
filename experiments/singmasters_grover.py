"""
singmasters_grover.py
---------------------
Grover's search for Singmaster's Conjecture — small case on IBM hardware.

The problem:
    Singmaster's Conjecture asks whether any number appears 9+ times
    in Pascal's Triangle. We start small: find which ROWS contain
    the value 6 in a non-trivial way.

    6 appears at:
        C(4, 2) = 6  → row 4  (binary: 0100)
        C(6, 1) = 6  → row 6  (binary: 0110)

    These are non-symmetric appearances (not just C(n,k) = C(n,n-k)).
    So 6 is a small example of a number appearing in multiple distinct rows.

The circuit:
    4-qubit Grover's search over rows 0-15 (2^4 = 16 states).
    Oracle marks |0100⟩ (row 4) and |0110⟩ (row 6).
    After Grover iterations, these two states should have amplified probability.

    For 2 marked states in N=16:
        optimal iterations = floor(π/4 * sqrt(N/M)) = floor(π/4 * sqrt(8)) ≈ 2

Usage:
    python experiments/singmasters_grover.py

Results are printed to stdout with job IDs.
Run this, note the job IDs, then retrieve results with:
    python experiments/singmasters_grover.py --results <job_id>
"""

import os
import sys
import json
import math
import argparse

from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../.env"))

from qiskit import QuantumCircuit
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler

# ── Config ────────────────────────────────────────────────────────────────────

TARGET_VALUE   = 6          # The Pascal's Triangle value we're searching for
N_QUBITS       = 4          # 2^4 = 16 rows (rows 0-15)
SHOTS          = 1024
# Rows where TARGET_VALUE appears (non-trivially):
#   C(4,2)=6 → row 4 → binary "0100"
#   C(6,1)=6 → row 6 → binary "0110"
MARKED_ROWS    = [4, 6]     # integer row indices
MARKED_STATES  = ["0100", "0110"]  # big-endian binary strings

# Optimal Grover iterations for M=2 marked states in N=16:
# floor(π/4 * sqrt(N/M))
N_ITERATIONS = max(1, math.floor(math.pi / 4 * math.sqrt((2**N_QUBITS) / len(MARKED_STATES))))


def build_oracle(qc: QuantumCircuit, marked_states: list[str]) -> None:
    """
    Phase oracle: flip the phase of each marked state.

    For each marked state, we apply X gates to map that state to |1111⟩,
    apply a multi-controlled-Z to flip its phase, then undo the X gates.
    We repeat for each marked state.
    """
    for state in marked_states:
        # X gates on qubits where the target bit is '0'
        # Qiskit is little-endian: qubit 0 = rightmost bit of the string
        for i, bit in enumerate(reversed(state)):
            if bit == "0":
                qc.x(i)

        # Multi-controlled phase flip on all 4 qubits
        # CCX + CZ decomposition for 4-qubit controlled-Z:
        # Use mcx (multi-controlled X) on ancilla then CZ, but simpler:
        # h on last qubit → mcx → h on last qubit = multi-controlled Z
        qc.h(N_QUBITS - 1)
        qc.mcx(list(range(N_QUBITS - 1)), N_QUBITS - 1)
        qc.h(N_QUBITS - 1)

        # Undo X gates
        for i, bit in enumerate(reversed(state)):
            if bit == "0":
                qc.x(i)

        qc.barrier()


def build_diffusion(qc: QuantumCircuit) -> None:
    """
    Grover diffusion operator (inversion about the mean).
    Circuit: H⊗n → X⊗n → multi-controlled-Z → X⊗n → H⊗n
    """
    qc.h(range(N_QUBITS))
    qc.x(range(N_QUBITS))

    qc.h(N_QUBITS - 1)
    qc.mcx(list(range(N_QUBITS - 1)), N_QUBITS - 1)
    qc.h(N_QUBITS - 1)

    qc.x(range(N_QUBITS))
    qc.h(range(N_QUBITS))
    qc.barrier()


def build_circuit() -> QuantumCircuit:
    """Build the full Grover's circuit for Singmaster's small case."""
    qc = QuantumCircuit(N_QUBITS, N_QUBITS)

    # Step 1: superposition over all 16 row states
    qc.h(range(N_QUBITS))
    qc.barrier()

    # Step 2: Grover iterations
    for _ in range(N_ITERATIONS):
        build_oracle(qc, MARKED_STATES)
        build_diffusion(qc)

    # Step 3: measure
    qc.measure(range(N_QUBITS), range(N_QUBITS))
    return qc


def submit(backend_name: str = None) -> None:
    """Submit the circuit to IBM hardware."""
    token = os.getenv("IBM_QUANTUM_TOKEN")
    if not token:
        print("ERROR: IBM_QUANTUM_TOKEN not set in .env")
        sys.exit(1)

    service = QiskitRuntimeService(channel="ibm_quantum_platform", token=token)

    if backend_name:
        backend = service.backend(backend_name)
    else:
        # Pick least busy backend with enough qubits
        backends = [b for b in service.backends(operational=True)
                    if b.num_qubits >= N_QUBITS]
        backend = min(backends, key=lambda b: b.status().pending_jobs)

    print(f"\n{'='*60}")
    print(f"Singmaster's Conjecture — Grover's Search")
    print(f"{'='*60}")
    print(f"Target value:    {TARGET_VALUE}")
    print(f"Marked rows:     {MARKED_ROWS}  (binary: {MARKED_STATES})")
    print(f"Search space:    {2**N_QUBITS} rows (0-{2**N_QUBITS - 1})")
    print(f"Grover iters:    {N_ITERATIONS}")
    print(f"Backend:         {backend.name}")
    print(f"Shots:           {SHOTS}")
    print(f"{'='*60}\n")

    qc = build_circuit()
    print(f"Circuit depth (before transpile): {qc.depth()}")
    print(f"Gate counts: {dict(qc.count_ops())}\n")

    # Transpile
    pm = generate_preset_pass_manager(backend=backend, optimization_level=1)
    isa_circuit = pm.run(qc)
    print(f"Circuit depth (after transpile):  {isa_circuit.depth()}")

    # Submit
    sampler = Sampler(backend)
    job = sampler.run([isa_circuit], shots=SHOTS)
    job_id = job.job_id()

    print(f"\nJob submitted!")
    print(f"Job ID: {job_id}")
    print(f"\nTo get results, run:")
    print(f"  python experiments/singmasters_grover.py --results {job_id}")
    print(f"\nOr check status:")
    print(f"  python experiments/singmasters_grover.py --status {job_id}")


def get_status(job_id: str) -> None:
    """Check job status."""
    service = QiskitRuntimeService(
        channel="ibm_quantum_platform",
        token=os.getenv("IBM_QUANTUM_TOKEN")
    )
    job = service.job(job_id)
    print(f"Job {job_id}: {job.status()}")


def get_results(job_id: str) -> None:
    """Retrieve and interpret results."""
    service = QiskitRuntimeService(
        channel="ibm_quantum_platform",
        token=os.getenv("IBM_QUANTUM_TOKEN")
    )
    job = service.job(job_id)
    result = job.result()

    pub_result = result[0]
    bitarray = pub_result.data
    field = list(vars(bitarray).keys())[0]
    counts = getattr(bitarray, field).get_counts()

    total = sum(counts.values())

    print(f"\n{'='*60}")
    print(f"Singmaster's Grover — Results (job {job_id})")
    print(f"{'='*60}")
    print(f"\nTop 8 measured states:")

    sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    for state, count in sorted_counts[:8]:
        row = int(state, 2)
        pct = round(count / total * 100, 1)
        bar = "█" * int(pct / 2)
        marker = " ← MARKED (row found!)" if row in MARKED_ROWS else ""
        print(f"  |{state}⟩ (row {row:2d}): {count:4d} shots ({pct:5.1f}%) {bar}{marker}")

    # Success check
    marked_counts = {s: counts.get(s, 0) for s in MARKED_STATES}
    marked_total = sum(marked_counts.values())
    marked_pct = round(marked_total / total * 100, 1)
    uniform_pct = round(100 / (2**N_QUBITS), 1)  # what random would give

    print(f"\n{'='*60}")
    print(f"Marked rows combined: {marked_total}/{total} shots = {marked_pct}%")
    print(f"Uniform random would give: {uniform_pct}% per state ({uniform_pct * len(MARKED_STATES):.1f}% combined)")
    print(f"Grover amplification factor: {round(marked_pct / (uniform_pct * len(MARKED_STATES)), 2)}x")

    if marked_pct > uniform_pct * len(MARKED_STATES) * 1.5:
        print(f"\n✅ SUCCESS — Grover's found rows {MARKED_ROWS} where {TARGET_VALUE} appears in Pascal's Triangle!")
        print(f"   The quantum search amplified the correct rows above noise.")
    else:
        print(f"\n⚠️  NOISY — Hardware noise reduced amplification.")
        print(f"   The marked states were not significantly amplified.")
        print(f"   Try running on a lower-noise device or with more shots.")

    print(f"\nInterpretation:")
    print(f"  C(4,2) = 6  → Grover found row 4: {counts.get('0100', 0)} shots")
    print(f"  C(6,1) = 6  → Grover found row 6: {counts.get('0110', 0)} shots")
    print(f"\nNext step: search for 3003 (appears 6 times) across larger row space.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Singmaster's Conjecture — Grover's on IBM")
    parser.add_argument("--backend", help="IBM backend name (default: least busy)")
    parser.add_argument("--status", metavar="JOB_ID", help="Check job status")
    parser.add_argument("--results", metavar="JOB_ID", help="Get job results")
    args = parser.parse_args()

    if args.status:
        get_status(args.status)
    elif args.results:
        get_results(args.results)
    else:
        submit(args.backend)
