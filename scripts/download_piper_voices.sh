#!/bin/bash
# Download additional Piper TTS voices
# Run on server: sudo bash download_piper_voices.sh

DDIR="/var/lib/docker/volumes/voiceai_piper-data/_data"
BASE="https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0"

download_voice() {
    local lang_path=$1
    local voice_name=$2

    if [ -f "$DDIR/${voice_name}.onnx" ] && [ -s "$DDIR/${voice_name}.onnx" ]; then
        echo "SKIP: $voice_name (already exists)"
        return 0
    fi

    echo -n "Downloading $voice_name ... "
    wget -q -O "$DDIR/${voice_name}.onnx" "$BASE/${lang_path}/${voice_name}.onnx?download=true"
    wget -q -O "$DDIR/${voice_name}.onnx.json" "$BASE/${lang_path}/${voice_name}.onnx.json?download=true"

    local size=$(du -h "$DDIR/${voice_name}.onnx" 2>/dev/null | cut -f1)
    echo "OK ($size)"
}

echo "=== Downloading Piper TTS Voices ==="
echo ""

echo "--- Turkish (tr_TR) ---"
download_voice "tr/tr_TR/fahrettin/medium" "tr_TR-fahrettin-medium"
download_voice "tr/tr_TR/fettah/medium" "tr_TR-fettah-medium"

echo ""
echo "--- German (de_DE) ---"
download_voice "de/de_DE/thorsten/high" "de_DE-thorsten-high"
download_voice "de/de_DE/thorsten_emotional/medium" "de_DE-thorsten_emotional-medium"
download_voice "de/de_DE/eva_k/x_low" "de_DE-eva_k-x_low"
download_voice "de/de_DE/kerstin/low" "de_DE-kerstin-low"

echo ""
echo "--- English (en_US / en_GB) ---"
download_voice "en/en_US/lessac/high" "en_US-lessac-high"
download_voice "en/en_US/ryan/high" "en_US-ryan-high"
download_voice "en/en_US/kristin/medium" "en_US-kristin-medium"
download_voice "en/en_GB/cori/high" "en_GB-cori-high"

echo ""
echo "--- French (fr_FR) ---"
download_voice "fr/fr_FR/tom/medium" "fr_FR-tom-medium"
download_voice "fr/fr_FR/gilles/low" "fr_FR-gilles-low"

echo ""
echo "--- Spanish (es_ES / es_MX) ---"
download_voice "es/es_ES/davefx/medium" "es_ES-davefx-medium"
download_voice "es/es_MX/claude/high" "es_MX-claude-high"

echo ""
echo "--- Italian (it_IT) ---"
download_voice "it/it_IT/paola/medium" "it_IT-paola-medium"

echo ""
echo "=== Summary ==="
echo "Total voice files:"
ls -1 "$DDIR"/*.onnx 2>/dev/null | wc -l
echo ""
ls -lhS "$DDIR"/*.onnx 2>/dev/null
