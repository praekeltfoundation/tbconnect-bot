## happy path
* request_tbcheck
    - slot{"terms": null}
    - utter_welcome
    - tbcheck_terms_form
    - form{"name": "tbcheck_terms_form"}
    - slot{"terms": null}
    - slot{"terms": "yes"}
    - form{"name": null}
    - tbcheck_profile_form
    - form{"name": "tbcheck_profile_form"}
    - form{"name": null}
    - utter_start_tb_check
    - tbcheck_form
    - form{"name": "tbcheck_form"}
    - form{"name": null}
    - action_session_start

## happy path returning user
* request_tbcheck
    - slot{"terms": "yes"}
    - utter_welcome_back
    - tbcheck_profile_form
    - form{"name": "tbcheck_profile_form"}
    - form{"name": null}
    - utter_start_tb_check
    - tbcheck_form
    - form{"name": "tbcheck_form"}
    - form{"name": null}
    - action_session_start

## session start new
    - action_session_start
    - slot{"terms": null}

## session start returning
    - action_session_start
    - slot{"terms": "yes"}

## exit
* exit
    - action_exit
    - slot{"terms": null}
    - action_listen
