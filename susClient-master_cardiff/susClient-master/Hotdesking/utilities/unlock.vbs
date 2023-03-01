Set WshShell = WScript.CreateObject("WScript.Shell")

WshShell.SendKeys "%{TAB}"

WScript.Sleep 1000
WshShell.SendKeys WScript.Arguments(0)

WScript.Sleep 1000
WshShell.SendKeys "{ENTER}"