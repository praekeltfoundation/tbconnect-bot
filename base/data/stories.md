## happy path
* request_tbcheck
    - action_set_activation
    - action_study_restriction
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
    - tbcheck_form
    - form{"name": "tbcheck_form"}
    - form{"name": null}
    - group_arm_form
    - form{"name": "group_arm_form"}
    - form{"name": null}
    - action_session_start

## happy path returning user
* request_tbcheck
    - action_set_activation
    - action_study_restriction
    - slot{"terms": "yes"}
    - utter_welcome_back
    - tbcheck_profile_form
    - form{"name": "tbcheck_profile_form"}
    - form{"name": null}
    - tbcheck_form
    - form{"name": "tbcheck_form"}
    - form{"name": null}
    - group_arm_form
    - form{"name": "group_arm_form"}
    - form{"name": null}
    - action_session_start

## do optin
* opt_in
   - action_opt_in

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
