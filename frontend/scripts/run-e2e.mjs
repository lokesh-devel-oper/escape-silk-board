import { spawn, spawnSync } from "node:child_process";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const frontendDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const projectDir = path.resolve(frontendDir, "..");
const services = [];

function start(command, args, options) {
  const child = spawn(command, args, {
    ...options,
    detached: process.platform !== "win32",
    stdio: ["ignore", "pipe", "pipe"],
  });
  child.output = "";
  const collect = (chunk) => {
    child.output = `${child.output}${chunk}`.slice(-6000);
  };
  child.stdout.on("data", collect);
  child.stderr.on("data", collect);
  services.push(child);
  return child;
}

async function waitForHttp(url, child, label) {
  const deadline = Date.now() + 30_000;
  while (Date.now() < deadline) {
    if (child.exitCode !== null) {
      throw new Error(`${label} exited before it was ready.\n${child.output}`);
    }
    try {
      const response = await fetch(url);
      if (response.ok) return;
    } catch {
      // The service is still starting.
    }
    await new Promise((resolve) => setTimeout(resolve, 150));
  }
  throw new Error(`${label} did not become ready.\n${child.output}`);
}

function stopTree(child) {
  if (!child.pid || child.exitCode !== null) return;
  if (process.platform === "win32") {
    child.kill();
  } else {
    try {
      process.kill(-child.pid, "SIGTERM");
    } catch {
      // It may have exited between the check and signal.
    }
  }
}

let exitCode = 1;
try {
  const uv = process.env.UV || "uv";
  const sync = spawnSync(uv, ["sync", "--frozen", "--no-dev"], {
    cwd: projectDir,
    stdio: "inherit",
  });
  if (sync.status !== 0) {
    throw new Error("uv could not synchronize the locked backend environment.");
  }
  const backendPython =
    process.platform === "win32"
      ? path.join(projectDir, ".venv", "Scripts", "python.exe")
      : path.join(projectDir, ".venv", "bin", "python");
  const backend = start(
    backendPython,
    [
      "-m",
      "uvicorn",
      "backend.app.main:app",
      "--host",
      "127.0.0.1",
      "--port",
      "8765",
    ],
    {
      cwd: projectDir,
      env: {
        ...process.env,
        ALLOWED_ORIGINS: "http://127.0.0.1:4173",
        GEMINI_API_KEY: "",
        GEMINI_MODEL: "",
      },
    },
  );
  const vite = start(
    process.execPath,
    [path.join(frontendDir, "node_modules", "vite", "bin", "vite.js"), "--host", "127.0.0.1", "--port", "4173"],
    {
      cwd: frontendDir,
      env: { ...process.env, VITE_API_BASE_URL: "http://127.0.0.1:8765" },
    },
  );

  await Promise.all([
    waitForHttp("http://127.0.0.1:8765/health", backend, "FastAPI"),
    waitForHttp("http://127.0.0.1:4173", vite, "Vite"),
  ]);

  const playwright = spawn(
    process.execPath,
    [path.join(frontendDir, "node_modules", "@playwright", "test", "cli.js"), "test"],
    {
      cwd: frontendDir,
      env: { ...process.env, PLAYWRIGHT_FORCE_TTY: "0" },
      stdio: ["ignore", "pipe", "pipe"],
    },
  );
  exitCode = await new Promise((resolve) => {
    let output = "";
    let settled = false;
    const finish = (code) => {
      if (settled) return;
      settled = true;
      clearTimeout(hardTimeout);
      resolve(code);
    };
    const consume = (target) => (chunk) => {
      const text = String(chunk);
      target.write(text);
      output = `${output}${text}`.slice(-20_000);
      const plainOutput = output.replace(/\u001b\[[0-?]*[ -/]*[@-~]/g, "");
      const summarySeen = plainOutput.includes(" passed (") || plainOutput.includes(" failed (");
      if (summarySeen) {
        setTimeout(() => {
          const failed = /\n\s*\d+\s+failed/.test(plainOutput);
          stopTree(playwright);
          finish(failed ? 1 : 0);
        }, 300);
      }
    };
    const hardTimeout = setTimeout(() => {
      console.error("Playwright did not exit within the E2E time budget.");
      stopTree(playwright);
      finish(1);
    }, 115_000);

    playwright.stdout.on("data", consume(process.stdout));
    playwright.stderr.on("data", consume(process.stderr));
    playwright.once("error", (error) => {
      console.error(error);
      finish(1);
    });
    playwright.once("exit", (code) => finish(code ?? 1));
  });
} catch (error) {
  console.error(error instanceof Error ? error.message : error);
} finally {
  for (const service of services.reverse()) stopTree(service);
}

process.exitCode = exitCode;
