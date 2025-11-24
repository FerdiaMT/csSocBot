from flask import Flask
from threading import Thread
import logging

app = Flask('')

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

@app.route('/')
def home():
    return """<!DOCTYPE html>
<html>
    <head>
        <title>CS Soc Game Jam</title>
    </head>
    <body>
        <div class="container">
            <p id="title">
                The Game Jam's theme will be revealed in
            </p>
            <div class="timer-container">
                <div class="time-unit">
                    <div class="time-value" id="days">00</div>
                    <div class="time-label">Days</div>
                </div>
                <div class="separator">:</div>
                <div class="time-unit">
                    <div class="time-value" id="hours">00</div>
                    <div class="time-label">Hours</div>
                </div>
                <div class="separator">:</div>
                <div class="time-unit">
                    <div class="time-value" id="minutes">00</div>
                    <div class="time-label">Minutes</div>
                </div>
                <div class="separator">:</div>
                <div class="time-unit">
                    <div class="time-value" id="seconds">00</div>
                    <div class="time-label">Seconds</div>
                </div>
            </div>
        </div>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }

            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }

            .container {
                text-align: center;
                background: rgba(255, 255, 255, 0.95);
                padding: 60px 40px;
                border-radius: 20px;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                max-width: 700px;
                width: 100%;
            }

            #title {
                font-size: 28px;
                color: #333;
                margin-bottom: 40px;
                font-weight: 600;
                line-height: 1.4;
            }

            .timer-container {
                display: flex;
                justify-content: center;
                align-items: center;
                gap: 15px;
                margin-bottom: 20px;
            }

            .time-unit {
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 10px;
            }

            .time-value {
                font-size: 72px;
                font-weight: 700;
                color: #667eea;
                font-family: 'Courier New', monospace;
                text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.1);
                min-width: 90px;
            }

            .time-label {
                font-size: 14px;
                color: #666;
                text-transform: uppercase;
                letter-spacing: 2px;
            }

            .separator {
                font-size: 72px;
                font-weight: 700;
                color: #667eea;
                font-family: 'Courier New', monospace;
                margin-bottom: 30px;
            }

            @media (max-width: 600px) {
                .container {
                    padding: 40px 25px;
                }

                #title {
                    font-size: 22px;
                    margin-bottom: 30px;
                }

                .timer-container {
                    gap: 8px;
                }

                .time-value {
                    font-size: 48px;
                    min-width: 60px;
                }

                .separator {
                    font-size: 48px;
                }

                .time-label {
                    font-size: 11px;
                }
            }
        </style>
        <script>
            function timer(){
                //before game jam theme reveal 
                if(Date.now() < new Date("November 27, 2025 18:00:00").getTime()){
                    let themeReveal = new Date("November 27, 2025 18:00:00").getTime();
                    let currentTime = Date.now();
                    let timeLeft = themeReveal - currentTime;
                        
                    let seconds = Math.floor((timeLeft / 1000) % 60);
                    let minutes = Math.floor((timeLeft / (1000 * 60)) % 60);
                    let hours = Math.floor((timeLeft / (1000 * 60 * 60)) % 24);
                    let days = Math.floor(timeLeft / (1000 * 60 * 60 * 24));
                        
                    seconds = seconds.toString().padStart(2, '0');
                    minutes = minutes.toString().padStart(2, '0');
                    hours = hours.toString().padStart(2, '0');
                    
                    document.getElementById("title").innerHTML = "The Game Jam's theme will be revealed in";
                    document.getElementById("days").innerHTML = days;
                    document.getElementById("hours").innerHTML = hours;
                    document.getElementById("minutes").innerHTML = minutes;
                    document.getElementById("seconds").innerHTML = seconds;
                }else{
                    //after game jam theme reveal
                    let jamSubmissionCutOff = new Date("December 8, 2025 18:00:00").getTime();
                    let currentTime = Date.now();
                    let timeLeft = jamSubmissionCutOff - currentTime;
                        
                    let seconds = Math.floor((timeLeft / 1000) % 60);
                    let minutes = Math.floor((timeLeft / (1000 * 60)) % 60);
                    let hours = Math.floor((timeLeft / (1000 * 60 * 60)) % 24);
                    let days = Math.floor(timeLeft / (1000 * 60 * 60 * 24));
                        
                    seconds = seconds.toString().padStart(2, '0');
                    minutes = minutes.toString().padStart(2, '0');
                    hours = hours.toString().padStart(2, '0');
                    
                    document.getElementById("title").innerHTML = "Time remaining to submit your game";
                    document.getElementById("days").innerHTML = days;
                    document.getElementById("hours").innerHTML = hours;
                    document.getElementById("minutes").innerHTML = minutes;
                    document.getElementById("seconds").innerHTML = seconds;
                }
            }
            timer();
            setInterval(timer,1000);
        </script>
    </body>
</html>"""

def run():
    try:
        app.run(host='0.0.0.0', port=8080, use_reloader=False, debug=False)
    except Exception as e:
        print(f"Flask server failed to start: {e}")

def keep_alive():
    t = Thread(target=run, daemon=True)
    t.start()
    print("Flask thread started")