from django.shortcuts import render

def home(request):
    return render(request, 'home.html')

def chat(request):
    return render(request, 'chat.html') 