import psutil
import docker
from docker.errors import DockerException
from datetime import datetime, timezone, timedelta
import subprocess
import re

MINSK_TZ = timezone(timedelta(hours=3))
docker_client = docker.from_env()

def get_server_status() -> dict:
    try:
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        return {
            'ok': True,
            'cpu': cpu,
            'ram_percent': ram.percent,
            'ram_used': ram.used,
            'ram_total': ram.total,
            'disk_percent': disk.percent,
            'disk_used': disk.used,
            'disk_total': disk.total,
            'error': None,
        }
    except Exception as e:
        return {'ok': False, 'error': str(e)}

def get_docker_stats() -> dict:
    try:
        docker_client.ping()
        containers = docker_client.containers.list(all=True)
        total = len(containers)
        running = len([c for c in containers if c.status == 'running'])
        stopped = total - running
        names = [f"{c.name} ({c.status})" for c in containers]
        return {
            'ok': True,
            'total': total,
            'running': running,
            'stopped': stopped,
            'names': names,
            'error': None,
        }
    except DockerException as e:
        return {'ok': False, 'error': f"Docker error: {e}"}
    except Exception as e:
        return {'ok': False, 'error': str(e)}

def bytes_to_gb(value: int) -> float:
    return round(value / 1024 / 1024 / 1024, 1)

def get_cloudflare_tunnels() -> dict:
    try:
        affine_url = subprocess.run([
            "journalctl", "-u", "cloudflared-affine.service",
            "--no-pager", "-n", "50"
        ], capture_output=True, text=True).stdout
        affine_url = re.search(r'https://[^ ]+\.trycloudflare\.com', affine_url)
        affine_url = affine_url.group(0) if affine_url else "Не найден"

        gitea_url = subprocess.run([
            "journalctl", "-u", "cloudflared-gitea.service",
            "--no-pager", "-n", "50"
        ], capture_output=True, text=True).stdout
        gitea_url = re.search(r'https://[^ ]+\.trycloudflare\.com', gitea_url)
        gitea_url = gitea_url.group(0) if gitea_url else "Не найден"

        return {
            'ok': affine_url != "Не найден" and gitea_url != "Не найден",
            'affine': affine_url,
            'gitea': gitea_url,
        }
    except Exception:
        return {'ok': False, 'affine': 'Ошибка', 'gitea': 'Ошибка'}


def build_status_block() -> str:
    s = get_server_status()
    d = get_docker_stats()
    timestamp = datetime.now(MINSK_TZ).strftime("%d.%m %H:%M:%S")

    WIDTH = 27  # ← Фиксированная ширина контента (27 символов)

    lines = []
    lines.append("#==========================#")

    # SERVER
    lines.append("#-----------SERVER---------#")
    if s.get('ok'):
        ram_used_gb = bytes_to_gb(s['ram_used'])
        ram_total_gb = bytes_to_gb(s['ram_total'])
        disk_used_gb = bytes_to_gb(s['disk_used'])
        disk_total_gb = bytes_to_gb(s['disk_total'])

        lines.append(f"# CPU: {s['cpu']:>5.1f}%".ljust(WIDTH) + "#")
        lines.append(f"# RAM: {ram_used_gb:>3.1f}/{ram_total_gb:>4.1f}G ({s['ram_percent']:>5.1f}%)".ljust(WIDTH) + "#")
        lines.append(
            f"# HDD: {disk_used_gb:>3.1f}/{disk_total_gb:>5.1f}G ({s['disk_percent']:>5.1f}%)".ljust(WIDTH) + "#")
    else:
        lines.append("# SERVER ERROR".ljust(WIDTH) + "          #")

    lines.append("#==========================#")
    lines.append("#-----------DOCKER---------#")

    # DOCKER
    if d.get('ok'):
        lines.append(f"# Containers: {d['total']:>2}".ljust(WIDTH) + "#")
        lines.append(f"# Running:    {d['running']:>2}".ljust(WIDTH) + "#")
        lines.append(f"# Stopped:    {d['stopped']:>2}".ljust(WIDTH) + "#")
        lines.append("#--------------------------#")

        names = d.get("names") or []
        if names:
            lines.append("# Containers:".ljust(WIDTH) + "#")
            for name in names[:2]:
                lines.append(f"# {name[:24]}".ljust(WIDTH) + "#")
        else:
            lines.append("# No containers".ljust(WIDTH) + "#")
    else:
        lines.append("# DOCKER ERROR".ljust(WIDTH) + "       #")
        lines.append("#--------------------------#")

    lines.append("#==========================#")
    lines.append("#----CLOUDFLARE-TUNNELS----#")

    # CLOUDFLARE
    tunnels = get_cloudflare_tunnels()
    if tunnels.get('ok'):
        lines.append(f"# AFFiNE: {tunnels['affine'][:24]}".ljust(WIDTH) + "#")
        lines.append(f"# Gitea:  {tunnels['gitea'][:24]}".ljust(WIDTH) + "#")
    else:
        lines.append("# AFFiNE: Не доступен".ljust(WIDTH) + "#")
        lines.append("# Gitea:  Не доступен".ljust(WIDTH) + "#")

    lines.append("#==========================#")
    lines.append(f"# Updated: {timestamp}".ljust(WIDTH) + "#")
    lines.append("#==========================#")

    return "\n".join(lines)

