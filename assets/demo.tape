Output assets/demo.gif

Set Shell "zsh"
Set FontSize 14
Set Width 1000
Set Height 650
Set Theme "Catppuccin Mocha"
Set Padding 16
Set Framerate 24
Set TypingSpeed 50ms
Set WindowBar Colorful
Set WindowBarSize 40

# Setup: ensure clean state
Hide
Type "export PATH=$PATH:/Users/alizaali/Library/Python/3.13/bin"
Enter
Type "cd /Users/alizaali/Documents/fixforward"
Enter
Type "fixforward rollback --path ./demo/broken_python 2>/dev/null; true"
Enter
Sleep 3s
Type "clear"
Enter
Sleep 500ms
Show

# Show the demo
Sleep 1s
Type "fixforward run --path ./demo/broken_python --no-confirm --no-animate"
Sleep 500ms
Enter

# Wait for full pipeline including Copilot CLI
Sleep 180s

# Hold final result
Sleep 8s
