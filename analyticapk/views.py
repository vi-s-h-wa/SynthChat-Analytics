from django.shortcuts import render, redirect
from django.views import View
from django.http import JsonResponse
import openai
from analyticapk.models import *
import pymongo
from transformers import pipeline 
from django.utils import timezone
from collections import defaultdict
from analyticapk import configs
from datetime import timedelta
import plotly.graph_objs as go
################################################################
#########                  LOGIN PAGE                 ##########
#########                                             ##########
################################################################
class login(View):
    def get(self, request):
        if request.session.get('authenticated'):
            username = request.session['username']
            messages = Messages.objects.all().filter(username=username)
            if username == configs.superadminusername:
                return render(request, 'admin.html')
            else:
                return render(request, 'chat.html', {'messages':messages,'username':username})
        return render(request, 'login.html')
    def post(self, request):
        if request.method == 'POST':
            username = request.POST.get('username')
            password = request.POST.get('password')
            client = pymongo.MongoClient('mongodb://localhost:27017/')
            db = client['chatgpt']
            collection = db["analyticapk_userdetails"]
            document = collection.find_one({"username": username})
            if username == configs.superadminusername and password == configs.superadminpassword:
                request.session['authenticated'] = True
                request.session['username'] = username
                noofusers = len(Userdetails.objects.all())
                noofmsg = len(Messages.objects.all())
                sessions = UserSession.objects.all()
                noofsess = len (sessions)
                total_time = timezone.timedelta()
                for session in sessions:
                    if session.login_time and session.logout_time:
                        session_duration = session.logout_time - session.login_time
                        total_time += session_duration

                user_sessions = UserSession.objects.all()

                # Prepare data for plotting
                login_counts = defaultdict(int)

                for session in user_sessions:
                    login_date = session.login_time.date()
                    login_counts[login_date] += 1

                # Prepare data for plotting
                dates = list(login_counts.keys())
                counts = list(login_counts.values())

                # Create a Plotly bar chart
                fig = go.Figure()
                fig.add_trace(go.Bar(x=dates, y=counts, name='Login Count'))

                # Update layout for better presentation
                fig.update_layout(title="User Login Count Per Day",
                xaxis_title="Date",
                yaxis_title="Login Count",
                xaxis=dict(type='date'),
                template="plotly_dark",
                font=dict(size=10), 
                width=400,
                height=300,
                )

                # Convert the figure to HTML and pass it to the template
                graph1 = fig.to_html()
                ############################################################################################
                # Group UserSession data by day and calculate total session time per day
                total_session_times = defaultdict(timedelta)

                for session in user_sessions:
                    login_date = session.login_time.date()
                    if session.logout_time is not None:
                        session_duration = session.logout_time - session.login_time
                        total_session_times[login_date] += session_duration

                # Prepare data for plotting
                dates = list(total_session_times.keys())
                total_session_times_list = [time.total_seconds() / 3600 for time in total_session_times.values()]

                # Create a Plotly bar chart
                fig = go.Figure()
                fig.add_trace(go.Bar(x=dates, y=total_session_times_list, name='Total Session Time (hours)'))

                # Update layout for better presentation
                fig.update_layout(title="Total Session Time Per Day",
                                xaxis_title="Date",
                                yaxis_title="Total Session Time (hours)",
                                xaxis=dict(type='date'),
                                template="plotly_dark",
                                font=dict(size=10),   # Set font size for text elements
                                width=400,  # Set the width of the graph in pixels
                                height=300,
                                )

                # Convert the figure to HTML and pass it to the template
                graph2 = fig.to_html()
                context={
                    'timespent':total_time,
                    'msgs':noofmsg,
                    'sess':noofsess,
                    'users': noofusers,
                    'graph1': graph1,
                    'graph2': graph2,
                }
                return render(request, 'admin.html',context)
            if document:
                stored_password = document.get("password")
                if stored_password == password:
                    request.session['authenticated'] = True
                    request.session['username'] = username
                    UserSession.objects.create(username=username, login_time=timezone.now())
                    messages = Messages.objects.all().filter(username=username)
                    if len(messages)==0:
                        emotion = 'NEUTRAL'
                    else:
                        emotion = messages[len(messages)-1].emotion
                    return render(request, 'chat.html', {'messages':messages,'username':username,'emotion':emotion})
                else:
                    return render(request, 'login.html',{'error':'Password is incorrect!!'})
            else:
                return render(request, 'login.html',{'error':'Username not found!!'})
            
################################################################
#########                  CHATGPT API                ##########
#########                                             ##########
################################################################
def chatgpt(request):
    if request.method == 'POST':
        inputtext = request.POST.get('input')
        username = request.POST.get('username')
        openai.api_key = "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"
        answer=openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": inputtext}
            ]
        )
        output = answer['choices'][0]['message']['content']
        if Messages.objects.filter(username = username):
            s = ''
            all = Messages.objects.filter(username=username)
            num_records = len(all)
            for i in range(num_records - 1, max(num_records - 4, -1), -1):
                s += all[i].user + ' '
            senti = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")
            senti=senti(s)
            if senti[0]['score'] > 0.9:
                emotion = senti[0]['label']
            else:
                emotion = 'NEUTRAL'
        else:
            emotion = 'NEUTRAL'
        Messages.objects.create(
           username = username, user = inputtext , reply = output , emotion = emotion
        )
        return JsonResponse({'message': output})
    
################################################################
#########               REGISTER PAGE                 ##########
#########                                             ##########
################################################################
class register(View):
    def get(self, request):
        return render(request, 'register.html')
    def post(self, request):
        if request.method == 'POST':
            username = request.POST.get('username')
            password = request.POST.get('password')
            email = request.POST.get('email')
            Userdetails.objects.create(
            username = username,password = password,email = email,
            )
            return redirect('login')

################################################################
#########              SESSION LOGOUT                 ##########
#########                                             ##########
################################################################
class Logout(View):
    def get(self, request):
        user = request.session['username']
        if user != configs.superadminusername:
            user_session = UserSession.objects.filter(username=user, logout_time=None).order_by('-login_time').first()
            if user_session:
                user_session.logout_time = timezone.now()
                user_session.save()
            UserSession.objects.filter(username=user, logout_time=None).delete()
        request.session.clear()
        return redirect('login')
    
################################################################
#########                 SEARCH BAR                  ##########
#########                                             ##########
################################################################
def search(request):
    if request.method == 'POST':
        un = request.POST.get('username')
        noofmsg = len(Messages.objects.all().filter(username = un))
        sessions = UserSession.objects.all().filter(username = un)
        noofsess = len (sessions)
        total_time = timezone.timedelta()
        for session in sessions:
            if session.login_time and session.logout_time and session.username == un:
                session_duration = session.logout_time - session.login_time
                total_time += session_duration
        
        user_sessions = UserSession.objects.all()

        # Prepare data for plotting
        login_counts = defaultdict(int)

        for session in user_sessions:
            login_date = session.login_time.date()
            login_counts[login_date] += 1

        # Prepare data for plotting
        dates = list(login_counts.keys())
        counts = list(login_counts.values())

        # Create a Plotly bar chart
        fig = go.Figure()
        fig.add_trace(go.Bar(x=dates, y=counts, name='Login Count'))

        # Update layout for better presentation
        fig.update_layout(title="User Login Count Per Day",
        xaxis_title="Date",
        yaxis_title="Login Count",
        xaxis=dict(type='date'),
        template="plotly_dark",
        font=dict(size=10), 
        width=400,
        height=300,
        )

        # Convert the figure to HTML and pass it to the template
        graph1 = fig.to_html()
        ############################################################################################
        # Group UserSession data by day and calculate total session time per day
        total_session_times = defaultdict(timedelta)

        for session in user_sessions:
            login_date = session.login_time.date()
            if session.logout_time is not None:
                session_duration = session.logout_time - session.login_time
                total_session_times[login_date] += session_duration

        # Prepare data for plotting
        dates = list(total_session_times.keys())
        total_session_times_list = [time.total_seconds() / 3600 for time in total_session_times.values()]

        # Create a Plotly bar chart
        fig = go.Figure()
        fig.add_trace(go.Bar(x=dates, y=total_session_times_list, name='Total Session Time (hours)'))

        # Update layout for better presentation
        fig.update_layout(title="Total Session Time Per Day",
                        xaxis_title="Date",
                        yaxis_title="Total Session Time (hours)",
                        xaxis=dict(type='date'),
                        template="plotly_dark",
                        font=dict(size=10),   # Set font size for text elements
                        width=400,  # Set the width of the graph in pixels
                        height=300,
                        )

        # Convert the figure to HTML and pass it to the template
        graph2 = fig.to_html()
        context={
            'timespent':total_time,
            'msgs':noofmsg,
            'sess':noofsess,
            'graph1': graph1,
            'graph2': graph2,
        }
        return JsonResponse(context)
