#!/bin/bash
set -e

echo "🔹 Updating system"
apt update -y

echo "🔹 Installing system dependencies"
apt install -y python3 python3-venv python3-pip curl unzip

echo "🔹 Creating virtual environment"
python3 -m venv venv
source venv/bin/activate

echo "🔹 Installing Python requirements"
pip install --upgrade pip
pip install -r requirements.txt

echo "🔹 Installing Deno"
curl -fsSL https://deno.land/install.sh | sh

echo "🔹 Adding Deno to PATH"
if ! grep -q ".deno/bin" ~/.bashrc; then
  echo 'export PATH="$HOME/.deno/bin:$PATH"' >> ~/.bashrc
fi

source ~/.bashrc

echo "✅ Setup complete!"
echo "➡️ Run: source venv/bin/activate"
echo "➡️ Check: deno --version"
