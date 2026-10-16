' Mo Dashboard Co Phieu - Chay an khong hien CMD
Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\Users\DELL\Desktop\AutoWebCoPhieu"

' Tat server cu neu dang chay
WshShell.Run "taskkill /F /IM python.exe", 0, True

' Cho 1 giay
WScript.Sleep 1000

' Chay server an (window state 0 = hidden)
WshShell.Run "cmd /c python server.py", 0, False

' Cho 3 giay de server khoi dong
WScript.Sleep 3000

' Mo Chrome o che do app (khong hien thanh dia chi)
WshShell.Run "chrome --app=http://localhost:5000", 1, False