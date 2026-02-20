import psutil
import docker
from docker.errors import DockerException

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

    lines = []
    lines.append("#=====================#")
    lines.append("# -----SERVER--------#")

    if s.get('ok'):
        ram_used_gb = bytes_to_gb(s['ram_used'])
        ram_total_gb = bytes_to_gb(s['ram_total'])
        disk_used_gb = bytes_to_gb(s['disk_used'])
        disk_total_gb = bytes_to_gb(s['disk_total'])

        lines.append(f"# CPU:  {s['cpu']:5.1f}%          #")
        lines.append(
            f"# RAM:  {ram_used_gb:4.1f}/{ram_total_gb:4.1f} Gb ({s['ram_percent']:5.1f}%) #"
        )
        lines.append(
            f"# HDD:  {disk_used_gb:4.1f}/{disk_total_gb:4.1f} Gb ({s['disk_percent']:5.1f}%) #"
        )
    else:
        lines.append("# SERVER STATS ERROR  #")
        err = (s.get('error') or 'unknown')[:19]
        lines.append(f"# {err:>19} #")

    lines.append("#=====================#")
    lines.append("# -----DOCKER--------#")

    if d.get('ok'):
        lines.append(f"# Containers: {d['total']:3d}           #")
        lines.append(f"# Running:    {d['running']:3d}           #")
        lines.append(f"# Stopped:    {d['stopped']:3d}           #")
        lines.append("#---------------------#")

        names = d.get("names") or []
        if names:
            lines.append("# List:              #")
            max_names = 10
            for name in names[:max_names]:
                short = name[:25]
                lines.append(f"# - {short:<21}#")
            if len(names) > max_names:
                lines.append(
                    f"# ... and {len(names) - max_names:3d} more  #"
                )
    else:
        lines.append("# DOCKER STATS ERROR #")
        err = (d.get('error') or 'unknown')[:19]
        lines.append(f"# {err:>19} #")

    lines.append("#=====================#")

    return "\n".join(lines)
