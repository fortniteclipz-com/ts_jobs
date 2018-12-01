import ts_aws.rds
import ts_aws.rds.clip
import ts_aws.rds.montage
import ts_aws.rds.montage_clip
import ts_aws.rds.stream_moment
import ts_aws.sqs.montage
import ts_logger
import ts_model.Clip
import ts_model.Montage
import ts_model.MontageClip
import ts_model.Status
import ts_model.Stream
import ts_model.StreamMoment

import shortuuid
import traceback

logger = ts_logger.get(__name__)

def run(event, context):
    try:
        logger.info("start", event=event, context=context)

        with ts_aws.rds.get_session() as session:
            query = session \
                .query(ts_model.Stream) \
                .outerjoin(ts_model.Montage, ts_model.Montage.stream_id == ts_model.Stream.stream_id) \
                .outerjoin(ts_model.StreamMoment, ts_model.StreamMoment.stream_id == ts_model.Stream.stream_id) \
                .filter(
                    ts_model.Montage.stream_id == None,
                    ts_model.StreamMoment.stream_id != None,
                    ts_model.Stream._status_analyze == ts_model.Status.DONE,
                ) \
                .group_by(ts_model.Stream.stream_id) \
                .order_by(ts_model.Stream._date_created.desc()) \
                .limit(3)
            logger.info("query", query=ts_aws.rds.print_query(query))
            streams = query.all()

        logger.info("streams", streams_length=len(streams))
        for s in streams:
            logger.info("stream", stream=s)
            montage_id = f"m-{shortuuid.uuid()}"
            clips = []
            montage_clips = []
            montage_duration = 0
            clip_moments = []
            stream_moments = ts_aws.rds.stream_moment.get_stream_moments(s)
            for i, sm in enumerate(stream_moments):
                if len(clip_moments) == 0 or (sm.time - clip_moments[len(clip_moments) - 1].time <= 5):
                    clip_moments.append(sm)
                    if i != len(stream_moments) - 1:
                        continue

                time_in = clip_moments[0].time - 4;
                if time_in < 0:
                    time_in = 0
                time_out = clip_moments[len(clip_moments) - 1].time + 1
                if time_out > s.duration:
                    time_out = s.duration

                clip_id = f"c-{shortuuid.uuid()}"
                clips.append(
                    ts_model.Clip(
                        clip_id=clip_id,
                        user_id='system',
                        stream_id=s.stream_id,
                        time_in=time_in,
                        time_out=time_out,
                    )
                )
                montage_clips.append(
                    ts_model.MontageClip(
                        montage_id=montage_id,
                        clip_id=clip_id,
                        clip_order=len(clips),
                    )
                )

                montage_duration += time_out - time_in
                clip_moments = [sm]
                if len(clips) == 50:
                    break

            montage = ts_model.Montage(
                montage_id=montage_id,
                user_id='system',
                stream_id=s.stream_id,
                streamer=s.streamer,
                duration=montage_duration,
                clips=len(clips),
                _status=ts_model.Status.WORKING,
            )

            ts_aws.rds.clip.save_clips(clips)
            ts_aws.rds.montage_clip.save_montage_clips(montage_clips)
            ts_aws.rds.montage.save_montage(montage)
            ts_aws.sqs.montage.send_message({
                'montage_id': montage.montage_id,
            })

        logger.info("success")
        return True

    except Exception as e:
        logger.error("error", _module=f"{e.__class__.__module__}", _class=f"{e.__class__.__name__}", _message=str(e), traceback=''.join(traceback.format_exc()))
        raise Exception(e) from None

