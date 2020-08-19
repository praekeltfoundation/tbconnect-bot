FROM rasa/rasa-sdk:1.10.1
WORKDIR /app
COPY requirements-actions.txt ./

# Change to root to install dependancies
USER root
RUN pip install -r requirements-actions.txt
USER 1001

COPY ./base/actions /app/base/actions
COPY ./base/data /app/base/data
CMD ["start", "--actions", "base.actions.actions"]
