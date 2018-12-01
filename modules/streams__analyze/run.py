import ts_aws.rds
import ts_aws.rds.stream
import ts_aws.sqs.stream__analyze
import ts_config
import ts_logger
import ts_model.Stream
import ts_model.Status

import json
import requests
import traceback

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
        video_ids = list(map(lambda v: v['id'], videos))
        logger.info("video_ids", video_ids=video_ids)

        with ts_aws.rds.get_session() as session:
            query = session \
                .query(ts_model.Stream) \
                .filter(
                    ts_model.Stream.stream_id.in_(video_ids),
                )
            logger.info("query", query=ts_aws.rds.print_query(query))
            streams = query.all()

        stream_ids = list(map(lambda s: s['stream_id'], streams))
        logger.info("stream_ids", stream_ids=stream_ids)

        for v in videos:
            logger.info("video", video=v)
            if v['id'] in stream_ids and v['user_name'].lower() is not 'fortnite':
                continue

            stream = ts_model.Stream(
                stream_id=v['id'],
                game='fortnite',
                _status_analyze=ts_model.Status.WORKING,
            )
            ts_aws.rds.stream.save_stream(stream)
            ts_aws.sqs.stream__analyze.send_message({
                'stream_id': stream.stream_id,
            })

            break

        logger.info("success")
        return True

    except Exception as e:
        logger.error("error", _module=f"{e.__class__.__module__}", _class=f"{e.__class__.__name__}", _message=str(e), traceback=''.join(traceback.format_exc()))
        raise Exception(e) from None

