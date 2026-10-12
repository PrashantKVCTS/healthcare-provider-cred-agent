# -*- mode: ruby -*-
# vi: set ft=ruby :

# ==============================================================================
# Vagrantfile for Healthcare Provider Credentialing Approval Agent VM
# Automated Local VM Provisioning (VirtualBox / Hyper-V)
# ==============================================================================

Vagrant.configure("2") do |config|
  # Base Linux Image: Ubuntu 22.04 LTS (Jammy)
  config.vm.box = "bento/ubuntu-22.04"
  config.vm.hostname = "cred-agent-vm"

  # Port Forwarding: Expose VM services to Host machine browser
  # FastAPI Web Operations Workbench & Appian Connected System API
  config.vm.network "forwarded_port", guest: 8000, host: 8000, host_ip: "127.0.0.1", auto_correct: true
  # Streamlit Operations & Committee Review Portal
  config.vm.network "forwarded_port", guest: 8501, host: 8501, host_ip: "127.0.0.1", auto_correct: true

  # VirtualBox Provider Settings
  config.vm.provider "virtualbox" do |vb|
    vb.name = "Healthcare-Credentialing-Agent-VM"
    vb.memory = "2048"
    vb.cpus = 2
    vb.customize ["modifyvm", :id, "--natdnshostresolver1", "on"]
  end

  # Hyper-V Provider Settings
  config.vm.provider "hyperv" do |hv|
    hv.vmname = "Healthcare-Credentialing-Agent-VM"
    hv.memory = 2048
    hv.cpus = 2
  end

  # Shell Provisioning Script: Run on first `vagrant up`
  config.vm.provision "shell", inline: <<-SHELL
    set -e
    echo "=========================================================="
    echo " Provisioning Healthcare Credentialing VM Environment..."
    echo "=========================================================="

    export DEBIAN_FRONTEND=noninteractive
    apt-get update -y
    apt-get install -y python3 python3-pip python3-venv curl git

    echo "[*] Setting up Python virtual environment..."
    python3 -m venv /opt/cred_agent_venv
    /opt/cred_agent_venv/bin/pip install --upgrade pip setuptools wheel
    /opt/cred_agent_venv/bin/pip install -r /vagrant/requirements.txt

    echo "[*] Running verification test suite..."
    cd /vagrant
    /opt/cred_agent_venv/bin/pytest tests/test_cred_agent.py -v

    echo "[*] Configuring systemd services for automatic startup..."

    # FastAPI Web Operations Workbench Systemd Service
    cat <<EOF > /etc/systemd/system/cred-agent-api.service
[Unit]
Description=Healthcare Credentialing Approval Agent API & Workbench
After=network.target

[Service]
Type=simple
User=vagrant
WorkingDirectory=/vagrant
Environment="PATH=/opt/cred_agent_venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="HOST=0.0.0.0"
Environment="PORT=8000"
ExecStart=/opt/cred_agent_venv/bin/python api/appian_api.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    # Streamlit Committee Portal Systemd Service
    cat <<EOF > /etc/systemd/system/cred-agent-ui.service
[Unit]
Description=Healthcare Credentialing Streamlit Committee Portal
After=network.target

[Service]
Type=simple
User=vagrant
WorkingDirectory=/vagrant
Environment="PATH=/opt/cred_agent_venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="HOST=0.0.0.0"
Environment="PORT=8501"
ExecStart=/opt/cred_agent_venv/bin/streamlit run ui/app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable cred-agent-api
    systemctl enable cred-agent-ui
    systemctl restart cred-agent-api
    systemctl restart cred-agent-ui

    echo "=========================================================="
    echo "  VM Provisioning Successfully Completed!"
    echo "  Services available on host browser:"
    echo "    - FastAPI Web Workbench: http://localhost:8000/ui"
    echo "    - Streamlit Committee:   http://localhost:8501"
    echo "    - Swagger API Docs:      http://localhost:8000/docs"
    echo "=========================================================="
  SHELL
end
