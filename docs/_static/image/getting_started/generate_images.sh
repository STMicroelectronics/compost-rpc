npx bit-field --vflip --hflip --vspace 110 --hspace 800 --compact -i msg_structure.json > msg_structure.svg
npx bit-field --vflip --hflip --vspace 60 --hspace 800 --compact -i example_read8_req.json > example_read8_req.svg
npx bit-field --vflip --hflip --vspace 60 --hspace 800 --compact -i example_read8_resp.json > example_read8_resp.svg
sed 's/stroke="black"/stroke="white" stroke-opacity="0.8"/g; s/font-weight="normal"/font-weight="normal" fill="white" fill-opacity="0.8"/g' msg_structure.svg > msg_structure_white.svg
sed 's/stroke="black"/stroke="white" stroke-opacity="0.8"/g; s/font-weight="normal"/font-weight="normal" fill="white" fill-opacity="0.8"/g' example_read8_req.svg > example_read8_req_white.svg
sed 's/stroke="black"/stroke="white" stroke-opacity="0.8"/g; s/font-weight="normal"/font-weight="normal" fill="white" fill-opacity="0.8"/g' example_read8_resp.svg > example_read8_resp_white.svg
