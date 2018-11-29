import ts_config
import ts_logger

import json
import requests
import traceback

from warrant import Cognito

logger = ts_logger.get(__name__)

def run(event, context):
    try:
        logger.info("start", event=event, context=context)

        twitch_url = "https://api.twitch.tv/helix/videos?game_id=33214&period=day&sort=views&language=en"
        r = requests.get(
            twitch_url,
            headers={
                'Content-Type': "application/json",
                'Client-ID': "xrept5ig71a868gn7hgte55ky8nbsa",
            }
        )
        videos = r.json()['data']
        logger.info("videos", videos_length=len(videos))

        user = Cognito(
            ts_config.get('cognito.pool-id'),
            ts_config.get('cognito.app-client-id'),
            username='sachinahj+ts_jobs@gmail.com'
        )
        user.authenticate(password='password')
        logger.info("user", user=user.__dict__)

        success = 0
        for video in videos:
            logger.info("video", video=video)
            ts_url = f"{ts_config.get('api-gateway.url')}/stream/{video['id']}/moments"
            response = requests.post(
                ts_url,
                headers={
                    'Content-Type': "application/json",
                    'Authorization': user.id_token,
                },
                data=json.dumps({
                    'game': 'fortnite',
                })
            )
            logger.info("response", response=response)
            if response.status_code == requests.codes.ok:
                success += 1
                if  success >= 1:
                    break

        logger.info("success")
        return True

    except Exception as e:
        logger.error("error", _module=f"{e.__class__.__module__}", _class=f"{e.__class__.__name__}", _message=str(e), traceback=''.join(traceback.format_exc()))
        raise Exception(e) from None

