#### This file contains tests to evaluate that your bot behaves as expected.
#### If you want to learn more, please see the docs: https://rasa.com/docs/rasa/user-guide/testing-your-assistant/

## happy path tbcheck
* request_tbcheck: check
  - action_set_activation
  - slot{"terms": null}
  - utter_welcome
  - tbcheck_terms_form
  - form{"name": "tbcheck_terms_form"}
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

## happy path tbcheck returning user
* request_tbcheck: check
  - action_set_activation
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
