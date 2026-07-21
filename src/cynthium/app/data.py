import os
from pathlib import Path

import pooch
import requests

GITHUB_URL = os.environ.get(
	"CYNTHIUM_DATA_BASE_URL",
	"https://github.com/osh3276/cynthium/releases/download/2.0.0/",
)

REGISTRY = {
	"DM1_20mpp_surf.tif": "sha256:ee4f80c10d87f24190448aa6d7ac67629e76b863ab7991bae94bee80589ad809",
	"DM1_final_adj_20mpp_slp.tif": "sha256:e09276123ea698fcb1decd01fa769068fbd2acc2418efe0eb47e966217db838d",
	"DM2_20mpp_surf.tif": "sha256:44448bb4ebd7c5814ec297e602e96d3af4b2cd3657956c2f4de174c48ab312bd",
	"DM2_final_adj_20mpp_slp.tif": "sha256:b1dc57374c07de83a796811d4e80a72c1c74810d6e3568b4f652a1efa908a18c",
	"Haworth_20mpp_surf.tif": "sha256:16a435fbcbe0edf46518856281db9f3f12c4787141791d3a69e398a4b64884eb",
	"Haworth_final_adj_20mpp_slp.tif": "sha256:219dcdad1636942fea8e8f3999a17b1d8ee92fb824ccbe661e10c496836f956b",
	"LM1_20mpp_surf.tif": "sha256:c4a82240e021f242cfb1a66821683ae456f0ae6d2067f0adee2c0dedad907478",
	"LM1_final_adj_20mpp_slp.tif": "sha256:9465176ab577e8f17a074d325a27d6d658530c5254382826cb3171688bff6381",
	"LM2_20mpp_surf.tif": "sha256:1cd8252b332cc6fb97366750115d350f30a7c27e88e01212aede5d0c16731bd5",
	"LM2_final_adj_20mpp_slp.tif": "sha256:b549b1e3cc624f5ec64e64676c5851717c9394f4d8cbce441893d5b7ef1063d3",
	"LM3_20mpp_surf.tif": "sha256:8fa44683fb7c0a75e99ffad4330d4c535ea87989ca961080e8e73d7e72bfb334",
	"LM3_final_adj_20mpp_slp.tif": "sha256:1bce1ae431fc596c6083c7fb0dee23be56534841a6bec58a5c9a8e155bcadc51",
	"LM4_20mpp_surf.tif": "sha256:7e980ab56c2424daf351db0fcf81f888b4d9b60cc0f93697f0ac84c9e1a47ce4",
	"LM4_final_adj_20mpp_slp.tif": "sha256:d4555b678b24673d99ae6245dc4704e5d4097b3b4be8df050d0834ced722e529",
	"LM5_20mpp_surf.tif": "sha256:e59c8f9c832f8bbafed6d1dd418d029b48ec796de2631b7942eea29edb12c4df",
	"LM5_final_adj_20mpp_slp.tif": "sha256:16e3d00916fbaaa329f16c01c45316a89e5d9231065481e0cfcaf333bb9ec1a5",
	"LM6_20mpp_surf.tif": "sha256:6473b596e273a6397576b34a96f7bca28527b6d8cabb816f590457769c33d8c7",
	"LM6_final_adj_20mpp_slp.tif": "sha256:dcbf78f58a4305d299036512f655e8144ac9d2f015494ebda0ebe080574d21fe",
	"LM7_20mpp_surf.tif": "sha256:4616de58743d7ff24d09e40c80b9c5de591f4d3fd6e384520567b4e82facd560",
	"LM7_final_adj_20mpp_slp.tif": "sha256:8a7f77d7e2ec16c9161fbf9d5f074730a41a6b9a23b2205c8a980f37e5fce49a",
	"LM8_20mpp_surf.tif": "sha256:fffcc3af18dd377ed5183baec8d3801f68d835b949905b40bcd377529764c396",
	"LM8_final_adj_20mpp_slp.tif": "sha256:75694145a3c13a136b813b5b1cddc6a6e78fd255fcf32a492f9636e2ad902aa0",
	"NPA_20mpp_surf.tif": "sha256:244cd6705ce1573fd259ee92c64a3068906f3ac2e2fa56300e1e884b110c72ab",
	"NPA_final_adj_20mpp_slp.tif": "sha256:16b6901d54c4fc496a985d08f69fed2c0bdb94756d80556424672540cef5dcb9",
	"NPB_20mpp_surf.tif": "sha256:4566b88f28243d646f57bbb94a4c44a227af4eb48a088aa375b6beb9990e96a5",
	"NPB_final_adj_20mpp_slp.tif": "sha256:210b897928b2dd4af9356468f108c18c8f3b53cb2d37e04f442b19aa9d4b6879",
	"NPC_20mpp_surf.tif": "sha256:ef525a20e23b4ff95b0a40fd8713401e3ac45232c815251f3291ee1d1cca6812",
	"NPC_final_adj_20mpp_slp.tif": "sha256:8dbfff47ca42fa24d252a7a15ccc313db1c361aab98672567607dbdc4abaf7d7",
	"NPD_20mpp_surf.tif": "sha256:18e89401e9158ff671b3a88c874ffff2728a8aaf76b9281711db54119def23d4",
	"NPD_final_adj_20mpp_slp.tif": "sha256:0a010192a644c396c323fd159050817424ccf1e0055827386387363c5c758b30",
	"SL2_20mpp_surf.tif": "sha256:a330ee3abc3b4688a6a5e29f39a2d835e94ef487ee4f1c61409ae5731e1987c6",
	"SL2_final_adj_20mpp_slp.tif": "sha256:7ba0bf98f39238b2cf8ff9a3ec2e075615b87943186ebad719def252ee6ae864",
	"SL3_final_adj_20mpp_slp.tif": "sha256:6694ebfc904a831867ab1f145ea5b1c03715bfedbb5fd7dfd37186bcc2046a29",
	"Shoemaker_20mpp_surf.tif": "sha256:085e27156bcd2d18d206a8f98340d925ab07ce8ac712c8779b933eff67958ec5",
	"Shoemaker_final_adj_20mpp_slp.tif": "sha256:f2c64c973310ad0a9cfa1b861a84452670ef8bdc85a09f4b63854418b9647390",
	"Site01_20mpp_surf.tif": "sha256:a8bbf312e89f7cbb6ae0d534b8bd514890bd98fc2e98fdcf5913d8746901ab19",
	"Site01_final_adj_20mpp_slp.tif": "sha256:7e5707a47f2a4b39e89908e5514e7227fe75f2ff542b09cd10cba87d1e9303e9",
	"Site04_20mpp_surf.tif": "sha256:ac00145082ce8119337c530137d1a856f15fc2591111a4d7ebd0e5b5af15f868",
	"Site04_final_adj_20mpp_slp.tif": "sha256:577cd832577ede43550dbb21e15a08b894c6250caa1ddf4f5b21f19ee3ade4ba",
	"Site06_20mpp_surf.tif": "sha256:f51015bda8ba27f55aa0a5825dc69f94c9910078849707f8cbadd9e0ba1d50c8",
	"Site06_final_adj_20mpp_slp.tif": "sha256:fbb124043da40b72c49eebd70e835a8fd73eb7f49b2a930fcccd9876ae28c408",
	"Site07_20mpp_surf.tif": "sha256:38042e132fa68cdb578e36ddf968ffee185dfc7f5de8882bde9769f7e7bd8715",
	"Site07_final_adj_20mpp_slp.tif": "sha256:796aff1f37a3c65bc22c0d9c8d4784c5db78b73e06c7e12cad0e154a7a2af4ef",
	"Site11_20mpp_surf.tif": "sha256:971bf5684efec277a984065b265ad3b1d696c959b62896e5fbdf33f4806baa65",
	"Site11_final_adj_20mpp_slp.tif": "sha256:aa751d4962aaeea1549c82d3d8ff9fe792b9b4e2c9215e3c6a63a7d35f7eae27",
	"Site20_20mpp_surf.tif": "sha256:1087bfb02c22e61ecef92039d52cb2d3cdcc5840d9fb74194919d2263fc42ed5",
	"Site20_final_adj_20mpp_slp.tif": "sha256:8611d628613121b1ff855ec451e1d3000bff2896c10d1b9555f76f9749bf21cd",
	"Site20v2_20mpp_surf.tif": "sha256:167bcbcbfee93af9e51dbea9567bba864d5b904394a73865dcad63c461b6a771",
	"Site20v2_final_adj_20mpp_slp.tif": "sha256:d44efb7c9c19c007ed952d37e7b52b09ab91c7ef3e3bb94fa05685cd8f44cf99",
	"Site23_20mpp_surf.tif": "sha256:72a3bae4994ce4ca2717334633323418626722dc8d8a1f2b8764acf59b8a2117",
	"Site23_final_adj_20mpp_slp.tif": "sha256:e1fa68990493ab1197b901df8dc82729c862963163245eb6dbe45a99e6f7c373",
	"Site42_20mpp_surf.tif": "sha256:347d8ed457313327db83ccf7eeb0ffa89c9710ec296e537cc2d3410819ea0598",
	"Site42_final_adj_20mpp_slp.tif": "sha256:224326645c4ca76ab3519086eeab9799779ffcb8a0cb1b9812628a5a6c3f82be",
	"illum.tif": "sha256:9977e5a3b31189841f3081994cb9748b8beedddeebdbb30b2aa9b5e86231d102",
	"illum_angle_0.tif": "sha256:214a280f6dc27ff54f4db6cf5b842d9f5ad3b67b01dc62a3ba0d90407d925cf6",
	"illum_angle_108.tif": "sha256:ea586535b492770e4492a68c4f4acf03caefc10f34cef8f0ce8c7b7c18d8187e",
	"illum_angle_12.tif": "sha256:c26358feaeafffb1cbff2be4c37f4508e2d42c0adcd629397a8a2f92c98e821b",
	"illum_angle_120.tif": "sha256:fac0a65b5d43de3ef57b0899e719f2ce40d9c865eb74bb49ea4e2aad7ab1cf64",
	"illum_angle_132.tif": "sha256:cc6ef5abf14732f3c1dd8e6b080396aa9d18c70ca106eda30309e4b6b9ebc07c",
	"illum_angle_144.tif": "sha256:9a7b65cc67b816911d5d3413063fb0b2716cf7b6decab60b251aecb709819bc1",
	"illum_angle_156.tif": "sha256:e03a5335a0456e8de8b0f9bac07981a66964567f7194618a15122755ac400b8c",
	"illum_angle_168.tif": "sha256:9daaa90e070d1a23728fde3c2d56f2756fdbe97cfdadfc244768ded93a765f43",
	"illum_angle_180.tif": "sha256:abd02d519aae5f5baea43a507aa13be1b955a0fdb312ff0c400b8316ad554414",
	"illum_angle_192.tif": "sha256:bf4769ed9e814ce5acc3a8f6149dd54bf344a48eed631d39ee986931935555e8",
	"illum_angle_204.tif": "sha256:036c5dccff540d849767c28f6bbd1b2e612550c84900aea94a95133113746386",
	"illum_angle_216.tif": "sha256:a34598634eb9578a447e88647cbd16ce5af20909418c22df360c71a367e3910e",
	"illum_angle_228.tif": "sha256:7c68f3a9b23bfbc807406e03b79c5c1cb4f491e6d4aed167188bb6bbeebedd8b",
	"illum_angle_24.tif": "sha256:060acecc0cf2e61d90ff5397abb9cf878645c7e90f83a1d4bc136c0d20a50dce",
	"illum_angle_240.tif": "sha256:b391d55594a6614e74ce883ceeef711d8934209586fbf7d7f9302b3692210708",
	"illum_angle_252.tif": "sha256:44d7d3d6c665d4474364a6e578693ac4f18b5c15049f66086f8b00effd20ca20",
	"illum_angle_264.tif": "sha256:2210e6263ad6559dfc90296cc160b83101c3bb8520e7e4329194bed78de960ed",
	"illum_angle_276.tif": "sha256:b9cefc25a1e7a3a8313a5576435fc7909d607d9b1fce6b310c23d90a3d959ed2",
	"illum_angle_288.tif": "sha256:8a94a6e04c05fed9720bf7441a43e0006a57bc773dc7472c21d208389ce2a718",
	"illum_angle_300.tif": "sha256:48b3660fdc2e21f49d38739e9131381d696a9584e5d4ae2086415b3ba94c0c0c",
	"illum_angle_312.tif": "sha256:629ebcaf6ac47eaf4d658b169b8622e62030db8b1b16c8203f7c2c6f9272e3c7",
	"illum_angle_324.tif": "sha256:b5db107158c5925aa7d949e5dd49d3f3448b701fe77ad53f8757bf976e395545",
	"illum_angle_336.tif": "sha256:f286b3245dee633f35242d3a23229056f37ec5dfd5b119b8f86792aedaddcc7c",
	"illum_angle_348.tif": "sha256:9c4fb98049580dce09b4fb48ab174277fedf1ecfe17bfb4f7e6b69e619acc396",
	"illum_angle_36.tif": "sha256:11b11a24d59e50e0615a5726dc6d2061c29ad21638e35d7768a31e61c0a67361",
	"illum_angle_48.tif": "sha256:62ffec85a6d150e94bdf30cec27ff715b1f32e75f1842dc6c3f97c7e3f541ffd",
	"illum_angle_60.tif": "sha256:adbd6e2a5cc4a0c29f006ade872926f77d813cde1dcee9fc05e7f05afd17ac5c",
	"illum_angle_72.tif": "sha256:bde21ffb51ae0441bf767ce699ad7482de4e2da6df5d8422364cf77fa9892b2b",
	"illum_angle_84.tif": "sha256:486137978f43391eab51e82cb9f3171387bf4c2b90d79dacb09eb428bbacfbe8",
	"illum_angle_96.tif": "sha256:e6c56542cefc113cec54adbfdaf3de4ca2511c61f9e762cba10e493dfeeb0a71",
	"meteor_energy.tif": "sha256:9cf99b8c259fa7f76afa48da96d60f72035c7a8656f77901f7796c2c67ebefba",
	"meteor_energy_angle_0.tif": "sha256:aeae09e36968847c93384025ac732b4a49ad93d33d879f91fb32779bb6622a0a",
	"meteor_energy_angle_108.tif": "sha256:d213b2e7d93ae770d3f56ba571cb13862e6366edbf2057241a10fd695abd80e7",
	"meteor_energy_angle_12.tif": "sha256:0e259ee6aa929728d18d843161b7b47be54e25d87989070a4db21db9016b4d8f",
	"meteor_energy_angle_120.tif": "sha256:59362fec09178da20491c126fabe4848ba4b7984976e72f6bc74f5928b979cf0",
	"meteor_energy_angle_132.tif": "sha256:8cb0f8709a4a18f9c2abfb748284a1217df1883872bc6fe5abba329255ff6b19",
	"meteor_energy_angle_144.tif": "sha256:18617faf495a6c571f375d3249865a3e3fd8864e231802789f508f1e2b542b98",
	"meteor_energy_angle_156.tif": "sha256:8943db84c3da232e72f3c4e3f5937ea7abbfe9cd11cf9a04e5ce4d483805b088",
	"meteor_energy_angle_168.tif": "sha256:94aa3c7c97ba8022a4831c3a4f590f42a398fa2594002848961058a2c1e5e75b",
	"meteor_energy_angle_180.tif": "sha256:90ec77a4f92b98d37c77b56e0e629f7874e0d0c4de9848f77b920bc4ed6bb8d3",
	"meteor_energy_angle_192.tif": "sha256:b36c1a3cf8d85f8aed2af38ea22893980e6d64e93ef1ef6e21801826e52e9243",
	"meteor_energy_angle_204.tif": "sha256:35d51025de801e8984eaa4de293bb5a8d1f50dd82998b70b8714d5a1745a79da",
	"meteor_energy_angle_216.tif": "sha256:5066f1af890d48a4279319d1f9c20771ad5481877dc730d6a3b40ddbd19b1987",
	"meteor_energy_angle_228.tif": "sha256:748957e34e44892368602fdcc3ce0a3405be3f8d195c13adfee22a392837e6bf",
	"meteor_energy_angle_24.tif": "sha256:993c80854b92141fcae4b1a6206fd0085f015fdd7cd34949394adacdfde5daca",
	"meteor_energy_angle_240.tif": "sha256:af3cfc742a98a43b6dcf5c97a17ac2cd79dd59a0ddb01253ce1b903a2b85c761",
	"meteor_energy_angle_252.tif": "sha256:888e48f694ddc2bb65d0091ce2be9bffddebe13490508c4f9e642e086600ff3d",
	"meteor_energy_angle_264.tif": "sha256:427cff52ecdc49ff280dd662fc99c6200019b9dfc34bde60a7f7c252dc194b49",
	"meteor_energy_angle_276.tif": "sha256:e2de6a743c562b10fdc527760bc3dd14f8ba1074e893483d4bb392db8bdbaab6",
	"meteor_energy_angle_288.tif": "sha256:9faf7e6bc68cea82fe954ce8f13bc0ff9137380d717930deeda79d4f3080c387",
	"meteor_energy_angle_300.tif": "sha256:134eec2f5ceccbedff929a2fcf530f19be17cf3dba9e56268b825306581e7322",
	"meteor_energy_angle_312.tif": "sha256:fa002a176ca71ab46edc85b9a7e7e44458f0a8b145e9d6f8fe109a745b6c7604",
	"meteor_energy_angle_324.tif": "sha256:0476d6286d88b521ec5581e7da925e653ef664060c710b3b867a0a93da009b34",
	"meteor_energy_angle_336.tif": "sha256:843f9848a33f5a801f333fc9650cf39d7e2c584fac7683a485a4898418aa7e79",
	"meteor_energy_angle_348.tif": "sha256:8effa239f91adff604005513ba768a90b5263e21579bd11df3465f141e70a8d2",
	"meteor_energy_angle_36.tif": "sha256:50015d1d338dc0d7090a73891245e2822bcb4e4ed3b9e2d902185f87cf755ea3",
	"meteor_energy_angle_48.tif": "sha256:cd6a1c8df9b30c61257ec6850f66ee84410018b2e0bd029b35fda28d56d64b4b",
	"meteor_energy_angle_60.tif": "sha256:9af1aecb4f91519db4b85e4d7c8deec99b09ec171640e362c652c56a5ff5a67f",
	"meteor_energy_angle_72.tif": "sha256:65026db294b7ca510dd1131acd104c7deed2dd4b2cdcf69e2564dab10bfe17b6",
	"meteor_energy_angle_84.tif": "sha256:f3624285422773d4ca1e7c15f561c01601bd6d5fe62eb6e25c7d97c13ca058e6",
	"meteor_energy_angle_96.tif": "sha256:7b24fe7418428f97c57f6b4efa84327d7225eb4d1a56c7e22f04f5e01891cd62",
	"meteor_number.tif": "sha256:d98acb6cc235b1b89f1ca9fda5c349c1e101ee960145b30b3d2173500bb24d09",
	"meteor_number_angle_0.tif": "sha256:7601c351ed2c9429f0ce1a1ff748bd34e2fcf009d2a3d4fd1e2cbd49e51f0050",
	"meteor_number_angle_108.tif": "sha256:bf20724cee03d6c31e61f5b8d1958e8a518a701fe68847d3b03ea838f9ccac41",
	"meteor_number_angle_12.tif": "sha256:9e64e5823542c6586447cec8d8cee0e839e41114bf11d9f1d686663936ea920a",
	"meteor_number_angle_120.tif": "sha256:789b079e209e4777d422c94006da8c084f29aa060c4c97e83fab7d0d7af726ab",
	"meteor_number_angle_132.tif": "sha256:dd46627462cde35559d5ca90fdaa8a6513cdc19e1c961974ba628b5372cbfea1",
	"meteor_number_angle_144.tif": "sha256:c39f9244f4952fcf6c627280414869c2f7cf37fdebd4b423d8c0da992cc4e76d",
	"meteor_number_angle_156.tif": "sha256:129331321953ef223a8ee6a7aae650b30b61194371c6f25aa5012b9cbaced4ec",
	"meteor_number_angle_168.tif": "sha256:333a065ee006feace0c8ff0a1b618eea3ee4d52d9b68c22ab711823f420af778",
	"meteor_number_angle_180.tif": "sha256:076f64907a5f72cc43a60d34f00723adab92c0c4c3be3cbbb1ab72d8aaa3e5d6",
	"meteor_number_angle_192.tif": "sha256:275095993f00db1f2fb46f2e4a1af3bf66a8698ad4c870bd616854cffb3e70e4",
	"meteor_number_angle_204.tif": "sha256:ce73427bb672c6010afc506d219f9477bcd8b31e64de42bc26867947c90cc0d6",
	"meteor_number_angle_216.tif": "sha256:b237b303b63348981295be2cd8efab3ad7496372dbc14bdec49a4ee4dd6b5c83",
	"meteor_number_angle_228.tif": "sha256:213e0886bb318204d25541255c100e4020bb4dbc6d07d0d69d3b85db5f952937",
	"meteor_number_angle_24.tif": "sha256:7da4f4cd290d632e94fea5f6b96e05b6b532d93969ad076a480114c94b098d43",
	"meteor_number_angle_240.tif": "sha256:1fad10bf136914979f4c51defd106d45b6e7d0476c7fe15a56684dd8431c474c",
	"meteor_number_angle_252.tif": "sha256:1f7f3410ca43ba4752ddf8fe42c131031ac7d223ad81ea8386793631935c2423",
	"meteor_number_angle_264.tif": "sha256:9371a482c2dfc63de4ecd5e0149430c96762bf34e740b4b489a0a67c307d641a",
	"meteor_number_angle_276.tif": "sha256:e4a23b4e5ec53e09996e977f145a9b91b54e9e1ca2f22109bc590ed1bdf1e2eb",
	"meteor_number_angle_288.tif": "sha256:f3fc3c60599679c9d37a8cee716c637a2d99a7857c962e585093e7a115f267f1",
	"meteor_number_angle_300.tif": "sha256:3dc80049f16e2bcac2bcc5285d8bf685ce75e556183cdd62036ef6f0ca066f43",
	"meteor_number_angle_312.tif": "sha256:83e25f3b09d577676894590a3c363937ffe441c081e2883940deb7f9a326ee06",
	"meteor_number_angle_324.tif": "sha256:5858efacbc698a5359470a87f7c09278c37966ec437a70183dc155d1251a9192",
	"meteor_number_angle_336.tif": "sha256:679dff549299c908a523be0a81d4b3364ea41ea6e32f8c8d539483475fdc79db",
	"meteor_number_angle_348.tif": "sha256:6ea6dc7e470bb970860e781318415d9bbd0cabebbe53efe2b9d90fd9efb34a78",
	"meteor_number_angle_36.tif": "sha256:e9f7f6f9a125dac17f16c2ee78cc4e7940ecaf231e42c30897842d346a765831",
	"meteor_number_angle_48.tif": "sha256:e87b690a1c4f76d485d2bd38ffb8159223f39292591aa0dc0152a51fbd7d65ac",
	"meteor_number_angle_60.tif": "sha256:447c13190370a8028a750900f23b5d7a7560cb62ab40c30071fb277b22d2a357",
	"meteor_number_angle_72.tif": "sha256:f3c78d37876291588192ea7af38dbc930f3ced96bc2bd99e0911eaca7941b5b9",
	"meteor_number_angle_84.tif": "sha256:8b77bec3df972158112afc6e1822de2f519d5baf44303ef8f1cc8f642c35e856",
	"meteor_number_angle_96.tif": "sha256:e4430097d5bafbaa91bd5c8c393edae6a7f8abfd009ea947c2cb734d852cd0b4",
	"polar_south_80_summer_avg-float.tif": "sha256:0be252e5fbaec7a12adf2e7ea04f2ade0ceefb3a6995f6ac68157e3a87d0b6b0",
	"polar_south_80_winter_avg-float.tif": "sha256:5f1fb5149a426d5749938111b57f5710b0522e874c8cad6ba36fca23682e6f85",
	"psr.tif": "sha256:e331998869b7d1b653bb6f01fc7c60910409f565eba4b4625e24eccdad26cdbe",
}

SPICE_KERNELS = (
	"naif0012.tls",
	"de430.bsp",
	"moon_pa_de440_200625.bpc",
	"moon_de440_250416.tf",
	"pck00011.tpc",
)

_store = pooch.create(
	path=os.environ.get("CYNTHIUM_DATA_DIR") or pooch.os_cache("cynthium"),
	base_url=GITHUB_URL,
	registry=REGISTRY,
)


def cache_dir() -> Path:
	return Path(str(_store.path))


def _gui_downloader(url, output_file, _pooch, check_only=None):
	"""Download a file with a live Qt progress dialog.

	Follows the pooch custom downloader signature:
	``(url, output_file, pooch, check_only=False)``.
	"""
	if check_only:
		return

	# Progress-bar download
	from PySide6.QtCore import Qt
	from PySide6.QtWidgets import QApplication, QProgressDialog

	fname = Path(output_file).name

	dialog = QProgressDialog(None)
	dialog.setWindowTitle("Downloading Data")
	dialog.setLabelText(f"Downloading {fname}...")
	dialog.setCancelButtonText("Cancel")
	dialog.setWindowModality(Qt.WindowModality.WindowModal)
	dialog.setMinimumDuration(0)
	dialog.setValue(0)
	dialog.show()
	QApplication.processEvents()

	try:
		resp = requests.get(url, stream=True, timeout=300)
		resp.raise_for_status()

		total = int(resp.headers.get("content-length", 0))
		downloaded = 0

		with open(output_file, "wb") as f:
			for chunk in resp.iter_content(chunk_size=65536):
				if dialog.wasCanceled():
					raise Exception("Download cancelled by user")
				if chunk:
					f.write(chunk)
					downloaded += len(chunk)
					if total:
						dialog.setMaximum(100)
						dialog.setValue(int(downloaded * 100 / total))
						dialog.setLabelText(
							f"Downloading {fname}...\n"
							f"{downloaded // 1024 // 1024}M / {total // 1024 // 1024}M"
						)
					QApplication.processEvents()
	except Exception:
		dialog.close()
		raise

	dialog.close()


def fetch(filename: str) -> str:
	"""Returns local path to the file, downloading if necessary.

	Shows a Qt progress dialog if a GUI application is running,
	otherwise falls back to the terminal tqdm progress bar.
	"""
	from PySide6.QtWidgets import QApplication

	app = QApplication.instance()
	if app is not None:
		return _store.fetch(filename, downloader=_gui_downloader)  # type: ignore[arg-type]
	return _store.fetch(filename, progressbar=True)

def fetch_all() -> dict[str, str]:
	"""Download all files. Returns {filename: local_path}."""
	return {name: fetch(name) for name in REGISTRY}
