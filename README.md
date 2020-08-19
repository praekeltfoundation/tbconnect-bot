# tbconnect-bot

## Running locally
```bash
~ export BOT=base
~ export LANG=en
~ pip install -r requirements.txt -r requirements-dev.txt -r requirements-actions.txt
~ ./shell.sh $BOT $LANG
```

### Running linting and tests
```bash
~ ./test.sh $BOT $LANG
```

### base
This is the main, public TBConnect bot.
It has the following languages:

`eng`: English
