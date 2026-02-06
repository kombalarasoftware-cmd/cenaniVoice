# VoiceAI Platform - Firewall Setup Script
# Run as Administrator!

Write-Host "Setting up firewall rules for VoiceAI Platform..." -ForegroundColor Cyan

# SIP UDP
New-NetFirewallRule -DisplayName "VoiceAI SIP UDP" -Direction Inbound -Protocol UDP -LocalPort 5060 -Action Allow -ErrorAction SilentlyContinue
New-NetFirewallRule -DisplayName "VoiceAI SIP UDP Out" -Direction Outbound -Protocol UDP -LocalPort 5060 -Action Allow -ErrorAction SilentlyContinue

# SIP TCP
New-NetFirewallRule -DisplayName "VoiceAI SIP TCP" -Direction Inbound -Protocol TCP -LocalPort 5060,5061 -Action Allow -ErrorAction SilentlyContinue
New-NetFirewallRule -DisplayName "VoiceAI SIP TCP Out" -Direction Outbound -Protocol TCP -LocalPort 5060,5061 -Action Allow -ErrorAction SilentlyContinue

# RTP Media
New-NetFirewallRule -DisplayName "VoiceAI RTP" -Direction Inbound -Protocol UDP -LocalPort 10000-10100 -Action Allow -ErrorAction SilentlyContinue
New-NetFirewallRule -DisplayName "VoiceAI RTP Out" -Direction Outbound -Protocol UDP -LocalPort 10000-10100 -Action Allow -ErrorAction SilentlyContinue

# AudioSocket
New-NetFirewallRule -DisplayName "VoiceAI AudioSocket" -Direction Inbound -Protocol TCP -LocalPort 9092 -Action Allow -ErrorAction SilentlyContinue

Write-Host "Firewall rules created successfully!" -ForegroundColor Green
