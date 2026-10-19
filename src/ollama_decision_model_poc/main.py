import os
import statistics
import time

from dotenv import load_dotenv
from typesafe_sdk import Choice, Noul, Score, TypeSafeClient

load_dotenv()

WARMUP_RUNS = int(os.getenv("WARMUP_RUNS", "1"))
BENCHMARK_RUNS = int(os.getenv("BENCHMARK_RUNS", "20"))

def build_questions():
    return {
        "team": Choice(
            instructions="Which team should handle this ticket?",
            criteria={
                "billing": "Payments and refunds",
                "technical": "Bugs and integrations",
                "other": "None of the above",
            },
        ),
        "refund": Noul(
            instructions="Does the customer explicitly ask for a refund?",
        ),
        "urgency": Score(
            instructions="How urgent is this ticket?",
            criteria=["Routine", "Soon", "Urgent"],
        ),
    }


def timed_call(client, state, questions):
    start = time.perf_counter()
    result = client.system_one(state=state, questions=questions)
    elapsed_ms = (time.perf_counter() - start) * 1000
    return result, elapsed_ms


def percentile(sorted_values, p):
    index = min(len(sorted_values) - 1, round(p / 100 * (len(sorted_values) - 1)))
    return sorted_values[index]


def print_result(result) -> None:
    print(f'team: {result.choices["team"].choice}')
    print(f"refund: {result.nouls['refund'].noul:.3f}")
    print(f"urgency: {result.scores['urgency'].score:.3f}")


def print_stats(latencies):
    ordered = sorted(latencies)
    print(f"runs:   {len(ordered)}")
    print(f"min:    {ordered[0]:.1f} ms")
    print(f"mean:   {statistics.mean(ordered):.1f} ms")
    print(f"median: {statistics.median(ordered):.1f} ms")
    print(f"p95:    {percentile(ordered, 95):.1f} ms")
    print(f"max:    {ordered[-1]:.1f} ms")
    if len(ordered) > 1:
        print(f"stdev:  {statistics.stdev(ordered):.1f} ms")
    print(f"throughput: {1000 / statistics.mean(ordered):.1f} decisions/s")


def main():
    ticket = "I was charged twice. Please refund the extra payment."
    state = {"ticket": ticket}
    questions = build_questions()

    with TypeSafeClient(timeout=120) as client:
        # Preload: the first request makes Ollama load the model into memory
        print("Loading model...")
        for i in range(WARMUP_RUNS):
            _, load_ms = timed_call(client, state, questions)
            print(f"  warm-up {i + 1}: {load_ms:.0f} ms")

        # Benchmark
        print(f"\nBenchmarking ({BENCHMARK_RUNS} runs)...")
        latencies = []
        result = None
        for _ in range(BENCHMARK_RUNS):
            result, ms = timed_call(client, state, questions)
            latencies.append(ms)

    print("\nResult:")
    print_result(result)

    print("\nLatency:")
    print_stats(latencies)


if __name__ == "__main__":
    main()
