-- Ejecutar en SUC1 y SUC2 (crear una vez). Requiere privilegio CREATE JOB.
-- Se deja deshabilitado hasta terminar las pruebas manuales.
BEGIN
 DBMS_SCHEDULER.CREATE_JOB(
  job_name=>'JOB_SYNC_CONECTADA',
  job_type=>'STORED_PROCEDURE',
  job_action=>'PKG_SYNC_CONECTADA.SINCRONIZACION_COMPLETA',
  start_date=>SYSTIMESTAMP,
  repeat_interval=>'FREQ=MINUTELY;INTERVAL=5',
  enabled=>FALSE,
  auto_drop=>FALSE,
  comments=>'Sincronizacion farmacia conectada cada cinco minutos'
 );
END;
/
-- ACTIVAR cuando termine la prueba manual:
-- BEGIN DBMS_SCHEDULER.ENABLE('JOB_SYNC_CONECTADA'); END;
-- /
-- DETENER antes de la demo de ejecucion a demanda:
-- BEGIN DBMS_SCHEDULER.DISABLE('JOB_SYNC_CONECTADA'); END;
-- /
-- Consultar estado:
SELECT job_name,enabled,state,last_start_date,next_run_date
FROM user_scheduler_jobs WHERE job_name='JOB_SYNC_CONECTADA';
