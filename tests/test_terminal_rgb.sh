#!/bin/bash
# Test if the terminal supports RGB colors

echo "=== Terminal RGB Support Test ==="
echo ""

# Test basic 16 colors (should work on all terminals)
echo -e "Basic ANSI color test:"
echo -e "\033[1;31mRed text\033[0m (should be red)"
echo -e "\033[1;33mYellow text\033[0m (should be yellow)"
echo -e "\033[1;32mGreen text\033[0m (should be green)"
echo -e "\033[1;36mCyan text\033[0m (should be cyan)"
echo ""

# Test RGB (24-bit) colors
echo "RGB (true color) test:"
echo -e "\033[38;2;255;100;0mOrange RGB text\033[0m (should be orange)"
echo -e "\033[38;2;255;255;0mYellow RGB text (full)\033[0m (should be bright yellow)"
echo -e "\033[38;2;127;127;0mYellow RGB text (50% dim)\033[0m (should be darker yellow)"
echo -e "\033[38;2;50;50;0mYellow RGB text (20% dim)\033[0m (should be very dark yellow)"
echo ""

echo "If you see colored text above, your terminal supports the colors."
echo "If RGB colors don't work, you'll see white text or escape codes."
echo ""
echo "Terminal type: $TERM"
echo "COLORTERM: $COLORTERM"
