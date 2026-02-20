import psutil
import docker
from docker.errors import DockerException
from datetime import datetime

import subprocess
import re

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
        return {
            'ok': False,
            'error': str(e),
        }


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
        return {
            'ok': False,
            'error': f"Docker error: {e}",
        }
    except Exception as e:
        return {
            'ok': False,
            'error': str(e),
        }


def bytes_to_gb(value: int) -> float:
    return round(value / 1024 / 1024 / 1024, 1)


def build_status_block() -> str:
    s = get_server_status()
    d = get_docker_stats()

    timestamp = datetime.now().strftime("%d.%m %H:%M:%S")  # ✅ ИСПРАВЛЕНО

    lines = []
    lines.append("#=============================#")
    lines.append("#-----------SERVER------------#")

    # ... SERVER блок без изменений ...

    lines.append("#=============================#")
    lines.append("#-----------DOCKER------------#")

    # ... DOCKER блок без изменений ...

    lines.append("#=============================#")
    lines.append("#----CLOUDFLARE-TUNNELS-------#")

    tunnels = get_cloudflare_tunnels()  # ✅ ПЕРЕМЕСТИ ВНУТРЬ ФУНКЦИИ
    if tunnels.get('ok'):
        lines.append(f"# AFFiNE: {tunnels['affine'][:28]:<28}#")  # ✅ #
        lines.append(f"# Gitea:  {tunnels['gitea'][:28]:<28}#")  # ✅ #
    else:
        lines.append("# AFFiNE: Не доступен          #")
        lines.append("# Gitea:  Не доступен          #")

    lines.append("#=============================#")
    lines.append(f"# Updated: {timestamp:<20}#")  # ✅ #
    lines.append("#=============================#")

    return "\n".join(lines)


def get_cloudflare_tunnels() -> dict:  # ✅ ИСПРАВЛЕН journalctl
    try:
        affine_url = subprocess.run([
            "journalctl", "-u", "cloudflared-affine.service",
            "--no-pager", "-n", "50"  # ✅ -n вместо n
        ], capture_output=True, text=True).stdout
        affine_url = re.search(r'https://[^ ]+\.trycloudflare\.com', affine_url)
        affine_url = affine_url.group(0) if affine_url else "Не найден"

        gitea_url = subprocess.run([
            "journalctl", "-u", "cloudflared-gitea.service",
            "--no-pager", "-n", "50"  # ✅ -n
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
