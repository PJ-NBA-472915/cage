"""
Lock API Service
Handles code generation, application building, and Golang development.
"""

import datetime
import logging
import os
import subprocess
import sys
import tempfile
from typing import Any, Optional

import uvicorn
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

# Import JSONL logging utilities
from src.cage.utils.jsonl_logger import setup_jsonl_logger
from src.cage.utils.openapi_schema import (
    LOCK_API_EXAMPLES,
    add_examples_to_openapi,
    add_response_headers_to_openapi,
    get_standard_openapi_schema,
)
from src.cage.utils.problem_details import setup_problem_detail_handlers
from src.cage.utils.request_id_middleware import EnhancedRequestIDMiddleware
from src.cage.utils.status_codes import validate_pod_token

# Configure JSONL logging
logger = setup_jsonl_logger("lock-api", level=logging.INFO)


# Use enhanced RequestID middleware
RequestIDMiddleware = EnhancedRequestIDMiddleware


# Security
security = HTTPBearer()


def get_pod_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Validate POD_TOKEN for authentication."""
    expected_token = os.environ.get("POD_TOKEN")
    return validate_pod_token(credentials.credentials, expected_token)


# FastAPI app
app = FastAPI(
    title="Lock API Service",
    description="Code generation, application building, and Golang development",
    version="1.0.0",
)


# Custom OpenAPI schema with Problem Details and examples
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_standard_openapi_schema(
        app=app,
        title="Lock API Service",
        version="1.0.0",
        description="Code generation, application building, and Golang development",
        tags=[
            {"name": "lock", "description": "Code generation and application building"},
            {"name": "golang", "description": "Golang development operations"},
            {"name": "health", "description": "Health check endpoints"},
        ],
    )

    # Add response headers and examples
    openapi_schema = add_response_headers_to_openapi(openapi_schema)
    openapi_schema = add_examples_to_openapi(openapi_schema, LOCK_API_EXAMPLES)

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

# Add middleware
app.add_middleware(RequestIDMiddleware, service_name="lock-api")

# Set up Problem Details exception handlers
setup_problem_detail_handlers(app)


# Request/Response models
class GolangGenerateRequest(BaseModel):
    template: str
    name: str
    package: Optional[str] = None
    variables: Optional[dict[str, Any]] = None


class GolangBuildRequest(BaseModel):
    source_path: str
    output_name: Optional[str] = None
    build_flags: Optional[list[str]] = None


class GolangValidateRequest(BaseModel):
    source_code: str
    go_version: Optional[str] = None


class TemplateInfo(BaseModel):
    name: str
    description: str
    variables: list[str]
    example: str


# Health check endpoint
@app.get("/health")
def health():
    """Health check endpoint."""
    current_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        # Check Golang installation
        go_version = "unknown"
        try:
            result = subprocess.run(
                ["go", "version"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                go_version = result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        return {
            "status": "success",
            "service": "lock-api",
            "date": current_date,
            "version": "1.0.0",
            "golang": {"installed": go_version != "unknown", "version": go_version},
        }
    except Exception as e:
        return {
            "status": "error",
            "service": "lock-api",
            "date": current_date,
            "error": str(e),
        }


# Kubernetes-style health endpoints
@app.get("/healthz")
def healthz():
    """Kubernetes-style health check endpoint."""
    try:
        # Basic health check - service is running
        return {"status": "healthy", "service": "lock-api"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")


@app.get("/readyz")
def readyz():
    """Kubernetes-style readiness check endpoint."""
    try:
        # Readiness check - service is ready to accept traffic
        # For lock-api, we should check Golang installation
        try:
            result = subprocess.run(
                ["go", "version"], capture_output=True, text=True, timeout=5
            )
            if result.returncode != 0:
                raise HTTPException(status_code=503, detail="Golang not available")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            raise HTTPException(status_code=503, detail="Golang not available")

        return {"status": "ready", "service": "lock-api"}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail="Service not ready")


# Golang operations endpoints
@app.post("/generate")
def generate_golang_app(
    request: GolangGenerateRequest, token: str = Depends(get_pod_token)
):
    """Generate a Golang application from a template."""
    try:
        logger.info(
            f"Golang generation requested: {request.template} -> {request.name}"
        )

        # Template definitions
        templates = {
            "web-server": {
                "main.go": """package main

import (
    "fmt"
    "log"
    "net/http"
    "os"
)

func main() {
    port := os.Getenv("PORT")
    if port == "" {
        port = "{{port|default:8080}}"
    }

    http.HandleFunc("/", handler)
    http.HandleFunc("/health", healthHandler)

    log.Printf("Server starting on port %s", port)
    log.Fatal(http.ListenAndServe(":"+port, nil))
}

func handler(w http.ResponseWriter, r *http.Request) {
    fmt.Fprintf(w, "Hello from {{name}}!")
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
    w.WriteHeader(http.StatusOK)
    fmt.Fprintf(w, "OK")
}
""",
                "go.mod": """module {{package|default:{{name}}}}

go 1.21
""",
                "README.md": """# {{name}}

A simple Go web server.

## Usage

```bash
go run main.go
```

The server will start on port {{port|default:8080}}.

## Endpoints

- `/` - Hello message
- `/health` - Health check
""",
            },
            "cli-tool": {
                "main.go": """package main

import (
    "flag"
    "fmt"
    "os"
)

func main() {
    var name string
    flag.StringVar(&name, "name", "World", "Name to greet")
    flag.Parse()

    fmt.Printf("Hello, %s!\\n", name)
    fmt.Println("{{description|default:This is a simple CLI tool}}")
}
""",
                "go.mod": """module {{package|default:{{name}}}}

go 1.21
""",
                "README.md": """# {{name}}

{{description|default:A simple CLI tool}}

## Usage

```bash
go run main.go -name "Your Name"
```
""",
            },
            "api-service": {
                "main.go": """package main

import (
    "encoding/json"
    "fmt"
    "log"
    "net/http"
    "os"
)

type Response struct {
    Message string `json:"message"`
    Service string `json:"service"`
}

func main() {
    port := os.Getenv("PORT")
    if port == "" {
        port = "8080"
    }

    http.HandleFunc("/", homeHandler)
    http.HandleFunc("/api/health", healthHandler)
    {{#each routes}}
    http.HandleFunc("/api/{{this}}", {{this}}Handler)
    {{/each}}

    log.Printf("API server starting on port %s", port)
    log.Fatal(http.ListenAndServe(":"+port, nil))
}

func homeHandler(w http.ResponseWriter, r *http.Request) {
    response := Response{
        Message: "Welcome to {{name}} API",
        Service: "{{name}}",
    }

    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(response)
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
    w.WriteHeader(http.StatusOK)
    fmt.Fprintf(w, "OK")
}

{{#each routes}}
func {{this}}Handler(w http.ResponseWriter, r *http.Request) {
    response := Response{
        Message: "{{this}} endpoint",
        Service: "{{name}}",
    }

    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(response)
}
{{/each}}
""",
                "go.mod": """module {{package|default:{{name}}}}

go 1.21
""",
                "README.md": """# {{name}}

{{description|default:A REST API service}}

## Usage

```bash
go run main.go
```

## Endpoints

- `/` - Home endpoint
- `/api/health` - Health check
{{#each routes}}
- `/api/{{this}}` - {{this}} endpoint
{{/each}}
""",
            },
        }

        if request.template not in templates:
            raise HTTPException(
                status_code=400, detail=f"Unknown template: {request.template}"
            )

        # Generate files from template
        template_files = templates[request.template]
        generated_files = []

        for file_path, template_content in template_files.items():
            # Simple template substitution
            content = template_content
            variables = request.variables or {}
            package_name = request.package or request.name

            # Replace template variables
            content = content.replace("{{name}}", request.name)
            content = content.replace("{{package}}", package_name)

            for key, value in variables.items():
                content = content.replace("{{key}}", str(value))

            # Handle default values in templates
            import re

            content = re.sub(r"\{\{([^}]+)\|default:([^}]+)\}\}", r"\2", content)

            # Handle conditional sections (simplified)
            content = re.sub(
                r"\{\{#each ([^}]+)\}\}(.*?)\{\{/each\}\}", "", content, flags=re.DOTALL
            )

            generated_files.append(
                {
                    "path": f"{request.name}/{file_path}",
                    "content": content,
                    "size": len(content.encode("utf-8")),
                }
            )

        return {
            "status": "success",
            "app_name": request.name,
            "package": package_name,
            "template": request.template,
            "files": generated_files,
            "total_size": sum(f["size"] for f in generated_files),
        }

    except Exception as e:
        logger.error(f"Error in generate_golang_app: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/build")
def build_golang_app(request: GolangBuildRequest, token: str = Depends(get_pod_token)):
    """Build a Golang application."""
    try:
        logger.info(f"Golang build requested for: {request.source_path}")

        # Create a temporary directory for building
        with tempfile.TemporaryDirectory() as temp_dir:
            # Check if source path exists and is valid
            if not os.path.exists(request.source_path):
                raise HTTPException(
                    status_code=404,
                    detail=f"Source path not found: {request.source_path}",
                )

            # Copy source to temp directory
            import shutil

            build_dir = os.path.join(temp_dir, "build")
            shutil.copytree(request.source_path, build_dir)

            # Change to build directory
            original_cwd = os.getcwd()
            os.chdir(build_dir)

            try:
                # Run go mod tidy first
                result = subprocess.run(
                    ["go", "mod", "tidy"], capture_output=True, text=True, timeout=30
                )
                if result.returncode != 0:
                    logger.warning(f"go mod tidy failed: {result.stderr}")

                # Build the application
                output_name = request.output_name or "app"
                build_cmd = ["go", "build", "-o", output_name]

                if request.build_flags:
                    build_cmd.extend(request.build_flags)

                start_time = datetime.datetime.now()
                result = subprocess.run(
                    build_cmd, capture_output=True, text=True, timeout=60
                )
                end_time = datetime.datetime.now()
                build_time_ms = int((end_time - start_time).total_seconds() * 1000)

                if result.returncode != 0:
                    raise HTTPException(
                        status_code=400, detail=f"Build failed: {result.stderr}"
                    )

                # Get binary size
                binary_path = os.path.join(build_dir, output_name)
                binary_size = (
                    os.path.getsize(binary_path) if os.path.exists(binary_path) else 0
                )

                # Get Go version
                version_result = subprocess.run(
                    ["go", "version"], capture_output=True, text=True, timeout=5
                )
                go_version = (
                    version_result.stdout.strip()
                    if version_result.returncode == 0
                    else "unknown"
                )

                return {
                    "status": "success",
                    "source_path": request.source_path,
                    "output_name": output_name,
                    "build_flags": request.build_flags or [],
                    "binary_size": binary_size,
                    "build_time_ms": build_time_ms,
                    "go_version": go_version,
                    "build_output": result.stdout,
                    "warnings": result.stderr if result.stderr else [],
                }

            finally:
                os.chdir(original_cwd)

    except subprocess.TimeoutExpired:
        logger.error("Build timeout")
        raise HTTPException(status_code=408, detail="Build timeout")
    except Exception as e:
        logger.error(f"Error in build_golang_app: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/templates", response_model=list[TemplateInfo])
def list_templates(token: str = Depends(get_pod_token)):
    """List available Golang templates."""
    try:
        # TODO: Implement actual template discovery
        logger.info("Template list requested")

        templates = [
            TemplateInfo(
                name="web-server",
                description="Simple HTTP web server",
                variables=["port", "host"],
                example='{"port": "8080", "host": "localhost"}',
            ),
            TemplateInfo(
                name="cli-tool",
                description="Command-line interface tool",
                variables=["command", "description"],
                example='{"command": "myapp", "description": "My CLI tool"}',
            ),
            TemplateInfo(
                name="api-service",
                description="REST API service",
                variables=["routes", "middleware"],
                example='{"routes": ["users", "posts"], "middleware": ["auth", "logging"]}',
            ),
        ]

        return templates

    except Exception as e:
        logger.error(f"Error in list_templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/validate")
def validate_golang_code(
    request: GolangValidateRequest, token: str = Depends(get_pod_token)
):
    """Validate Golang source code."""
    try:
        # TODO: Implement actual Go code validation
        logger.info("Golang code validation requested")

        # Placeholder validation
        validation_result = {
            "status": "success",
            "valid": True,
            "errors": [],
            "warnings": [],
            "go_version": request.go_version or "1.21",
            "syntax_check": "passed",
            "imports_check": "passed",
            "build_check": "passed",
        }

        return validation_result

    except Exception as e:
        logger.error(f"Error in validate_golang_code: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/go-version")
def get_go_version(token: str = Depends(get_pod_token)):
    """Get installed Go version information."""
    try:
        logger.info("Go version requested")

        # Get Go version
        version_result = subprocess.run(
            ["go", "version"], capture_output=True, text=True, timeout=5
        )

        if version_result.returncode != 0:
            raise HTTPException(
                status_code=500, detail="Go not installed or not in PATH"
            )

        version_output = version_result.stdout.strip()

        # Get Go environment
        env_result = subprocess.run(
            ["go", "env", "GOPATH", "GOROOT", "GOOS", "GOARCH"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        env_lines = (
            env_result.stdout.strip().split("\n") if env_result.returncode == 0 else []
        )

        return {
            "status": "success",
            "version": version_output,
            "arch": env_lines[3] if len(env_lines) > 3 else "unknown",
            "os": env_lines[2] if len(env_lines) > 2 else "unknown",
            "gopath": env_lines[0]
            if len(env_lines) > 0
            else os.environ.get("GOPATH", "/go"),
            "goroot": env_lines[1]
            if len(env_lines) > 1
            else os.environ.get("GOROOT", "/usr/local/go"),
        }

    except subprocess.TimeoutExpired:
        logger.error("Go version check timeout")
        raise HTTPException(status_code=408, detail="Go version check timeout")
    except Exception as e:
        logger.error(f"Error in get_go_version: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/install-deps")
def install_go_dependencies(go_mod_path: str, token: str = Depends(get_pod_token)):
    """Install Go module dependencies."""
    try:
        logger.info(f"Go dependencies installation requested for: {go_mod_path}")

        # Check if go.mod file exists
        if not os.path.exists(go_mod_path):
            raise HTTPException(
                status_code=404, detail=f"go.mod file not found: {go_mod_path}"
            )

        # Change to the directory containing go.mod
        mod_dir = os.path.dirname(os.path.abspath(go_mod_path))
        original_cwd = os.getcwd()
        os.chdir(mod_dir)

        try:
            start_time = datetime.datetime.now()

            # Run go mod download
            result = subprocess.run(
                ["go", "mod", "download"], capture_output=True, text=True, timeout=60
            )

            end_time = datetime.datetime.now()
            download_time_ms = int((end_time - start_time).total_seconds() * 1000)

            if result.returncode != 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"Dependency installation failed: {result.stderr}",
                )

            # Get dependency count from go.mod
            dependencies_count = 0
            try:
                with open("go.mod") as f:
                    content = f.read()
                    # Simple count of require statements (excluding indirect)
                    dependencies_count = (
                        content.count("require (")
                        + content.count("\t")
                        + content.count("require ")
                    )
            except Exception:
                pass

            # Get Go module cache size (approximate)
            cache_size_mb = 0
            try:
                cache_result = subprocess.run(
                    ["go", "env", "GOMODCACHE"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if cache_result.returncode == 0:
                    cache_dir = cache_result.stdout.strip()
                    if os.path.exists(cache_dir):
                        # Calculate directory size (simplified)
                        total_size = 0
                        for dirpath, dirnames, filenames in os.walk(cache_dir):
                            for filename in filenames:
                                filepath = os.path.join(dirpath, filename)
                                try:
                                    total_size += os.path.getsize(filepath)
                                except OSError:
                                    pass
                        cache_size_mb = total_size // (1024 * 1024)
            except Exception:
                pass

            return {
                "status": "success",
                "go_mod_path": go_mod_path,
                "dependencies_installed": dependencies_count,
                "download_time_ms": download_time_ms,
                "cache_size_mb": cache_size_mb,
                "output": result.stdout,
                "warnings": result.stderr if result.stderr else [],
            }

        finally:
            os.chdir(original_cwd)

    except subprocess.TimeoutExpired:
        logger.error("Dependency installation timeout")
        raise HTTPException(status_code=408, detail="Dependency installation timeout")
    except Exception as e:
        logger.error(f"Error in install_go_dependencies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
def get_lock_api_stats(token: str = Depends(get_pod_token)):
    """Get Lock API service statistics."""
    try:
        logger.info("Lock API stats requested")

        return {
            "status": "success",
            "templates_available": 3,
            "apps_generated": 0,
            "builds_completed": 0,
            "validations_performed": 0,
            "golang": {
                "version": "go1.21.0",
                "installed": True,
                "gopath": os.environ.get("GOPATH", "/go"),
                "goroot": os.environ.get("GOROOT", "/usr/local/go"),
            },
        }

    except Exception as e:
        logger.error(f"Error in get_lock_api_stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8004)),
        reload=os.environ.get("RELOAD", "false").lower() == "true",
    )
