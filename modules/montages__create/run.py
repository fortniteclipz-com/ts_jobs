import ts_aws.rds
import ts_config
import ts_logger
import ts_model.Montage
import ts_model.Status
import ts_model.Stream

import traceback

logger = ts_logger.get(__name__)

def run(event, context):
    try:
        logger.info("start", event=event, context=context)

        session = ts_aws.rds.get_session()
        query = session \
            .query(ts_model.Stream) \
            .outerjoin(ts_model.Montage, ts_model.Montage.stream_id == ts_model.Stream.stream_id) \
            .filter(
                ts_model.Montage.stream_id == None,
                ts_model.Stream._status_analyze == ts_model.Status.DONE,
            ) \
            .limit(5)

        logger.info("query", query=ts_aws.rds.print_query(query))
        streams = query.all()
        logger.info("streams", streams_length=len(streams))

        for s in streams:
            logger.info("stream", s=s)




        logger.info("success")
        return True

    except Exception as e:
        logger.error("error", _module=f"{e.__class__.__module__}", _class=f"{e.__class__.__name__}", _message=str(e), traceback=''.join(traceback.format_exc()))
        raise Exception(e) from None

