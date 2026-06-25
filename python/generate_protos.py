import os
import subprocess
import sys


def generate_protos():
    print("[Python] Generating gRPC and Protobuf code...")
    proto_dir = os.path.join("..", "shared", "protos")
    proto_file = os.path.join(proto_dir, "bot.proto")

    # Run the grpc_tools.protoc compiler
    command = [
        sys.executable,
        "-m",
        "grpc_tools.protoc",
        f"-I{proto_dir}",
        "--python_out=.",
        "--grpc_python_out=.",
        proto_file,
    ]

    try:
        subprocess.check_call(command)
        print("[Python] Done.")
    except Exception as e:
        print(f"[Python] Error generating: {e}")


if __name__ == "__main__":
    generate_protos()
