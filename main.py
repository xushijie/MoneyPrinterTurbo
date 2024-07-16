import uvicorn
from loguru import logger
from app.config import config
import threading


from app.controllers.manager import nacos_client as nc

if __name__ == '__main__':
    logger.info("start server, docs: http://127.0.0.1:" + str(config.listen_port) + "/docs")
    #nc.register()
    # Start the heartbeat thread
    #heartbeat_thread = threading.Thread(target=nc.send_heartbeat_to_nacos, daemon=True)
    #heartbeat_thread.start()
    
    uvicorn.run(app="app.asgi:app", host=config.listen_host, port=config.listen_port, reload=config.reload_debug,
                log_level="warning")
