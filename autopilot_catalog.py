import os
import json
import logging

logger = logging.getLogger(__name__)

AUTOPILOT_FILE = os.path.join(os.path.dirname(__file__), 'autopilot.json')
CATALOG_FILE = os.path.join(os.path.dirname(__file__), 'jobs_catalog.json')

def load_autopilot_state():
    default_state = {
        'enabled': True,
        'interval_hours': 6,
        'last_post': None,
        'current_index': 0
    }
    if not os.path.exists(AUTOPILOT_FILE):
        return default_state
    try:
        with open(AUTOPILOT_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for k, v in default_state.items():
                if k not in data:
                    data[k] = v
            return data
    except Exception as e:
        logger.error(f'Error cargando autopilot.json: {e}')
        return default_state

def save_autopilot_state(state):
    try:
        with open(AUTOPILOT_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f'Error guardando autopilot.json: {e}')
        return False

def get_autopilot_jobs_catalog():
    if os.path.exists(CATALOG_FILE):
        try:
            with open(CATALOG_FILE, 'r', encoding='utf-8') as f:
                jobs = json.load(f)
                if isinstance(jobs, list) and len(jobs) > 0:
                    return jobs
        except Exception as e:
            logger.error(f'Error leyendo jobs_catalog.json: {e}')
    return []
