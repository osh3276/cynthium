import os
from pathlib import Path

import pooch
import requests

GITHUB_URL = os.environ.get(
	"CYNTHIUM_DATA_BASE_URL",
	"https://github.com/osh3276/cynthium/releases/download/data-v1.1.0b1/",
)

REGISTRY = {
	"DM1_20mpp_surf.tif": "sha256:ee4f80c10d87f24190448aa6d7ac67629e76b863ab7991bae94bee80589ad809",
	"DM1_final_adj_20mpp_slp.tif": "sha256:e09276123ea698fcb1decd01fa769068fbd2acc2418efe0eb47e966217db838d",
	"DM2_20mpp_surf.tif": "sha256:44448bb4ebd7c5814ec297e602e96d3af4b2cd3657956c2f4de174c48ab312bd",
	"DM2_final_adj_20mpp_slp.tif": "sha256:b1dc57374c07de83a796811d4e80a72c1c74810d6e3568b4f652a1efa908a18c",
	"Haworth_20mpp_surf.tif": "sha256:16a435fbcbe0edf46518856281db9f3f12c4787141791d3a69e398a4b64884eb",
	"Haworth_final_adj_20mpp_slp.tif": "sha256:219dcdad1636942fea8e8f3999a17b1d8ee92fb824ccbe661e10c496836f956b",
	"Illumination_mask_80mpp_FULL_GEO.tif": "sha256:7181bc83ca527c4d4ab1f5b44ce187b28dbe13d4874c5879489640abdb2af456",
	"Illumination_mask_80mpp_Full_Region.tif": "sha256:86fe3d5a91ce6d6e994ee6206a6b98d96dda7e16b20d330eeaa9cd3960284c2b",
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
	"Summer_Illumination_mask_80mpp_SPole_GEO.tif": "sha256:e0c19ec2283779667fbba1c4eb67c6f15beb1833e4a61b0ee1312c7ac786e518",
	"Winter_Illumination_mask_80mpp_SPole_GEO.tif": "sha256:a6fec52f4d5669870ea47379d5d8e28558fbb6aad011af211949edea6353305b",
	"de430.bsp": "sha256:6e1b277c5f07135a84950604b83e56b736be696a7f3560bcddb1d4aeb944fca1",
	"illum_angle_108.tif": "sha256:65bd435c3bbbbd9686fd1943c068d987c66a349fd6240c6babc4aa61d1a15cad",
	"illum_angle_12.tif": "sha256:f0f1a479da4b163cfb46c147c40e0ba32112864c5bcd93695db963cd5199fa19",
	"illum_angle_120.tif": "sha256:57f9f5c8045d05f056ff9394200260f19fa70c8e1af7e58f94b96fc375e771f7",
	"illum_angle_132.tif": "sha256:15a2fc72f67c4e8fb45e540e64a6b42c3e927e2cc04962c36020b1190694a800",
	"illum_angle_144.tif": "sha256:e3ce7ccc15e81c0106f96df9a07b8201f1b2fd00f007e595b286de43b51eac1b",
	"illum_angle_156.tif": "sha256:1cdad2669f6a895b6e58b9b395b74cdccd8498820b77ecf8527fe2342521cc24",
	"illum_angle_168.tif": "sha256:d32a6c923d22e30b084ef1a36f55b016246726e52983726c9113a915801493d6",
	"illum_angle_180.tif": "sha256:4ae9d89a6f64b86339c5bd781bf90d61cf0d8213298c985da359af4bd34ea2c5",
	"illum_angle_192.tif": "sha256:f8d9578936cd590a8673d2588f0d89a7e3ac01ee5fd30e59aa1a565bfa92e499",
	"illum_angle_204.tif": "sha256:8b5e1be3f79184761b37d1cb1d99a0dd85a83ac3c91ee33df1bc9a5a7cbc8eba",
	"illum_angle_216.tif": "sha256:4c3219beb74e1ca7547e78d26960cd72578e79a536bc5403480491ea7524dd33",
	"illum_angle_228.tif": "sha256:a4bdf811db4c17bab9f6f1b112e08aa1519457d39359474e7243d581c792795a",
	"illum_angle_24.tif": "sha256:35130d734545c1b7f9b471981bd8b626805191b544af0f535411aa2a43584200",
	"illum_angle_240.tif": "sha256:95decbd191bc1e59b1145cf287661041dbe17a6f5b4c0c97b8d1a14340d1ef92",
	"illum_angle_252.tif": "sha256:790f7bffaf32011a8923f22d05c3f0688fc06f600e08fc9b02c19687f03ce566",
	"illum_angle_264.tif": "sha256:536a90a7048130326c9614ed35d238164b448460af8ad030dcbb657728000b94",
	"illum_angle_276.tif": "sha256:4466bfd4e73126b3fc7b945844122f475ffca40c11ae70e31fb89f29ceedd02a",
	"illum_angle_288.tif": "sha256:bdee3d16512109206e80cec2a54246a12ff832313e750979a2e4deb9370ce3f6",
	"illum_angle_300.tif": "sha256:18308fccd5c315acc3271e65f7cef740b669a899c9ca2ad6150db81ca732fdf6",
	"illum_angle_312.tif": "sha256:0adc32a6be9fb79b3bf76d4403211e10d971d8229535a02f49d0d3fcc7f2e879",
	"illum_angle_324.tif": "sha256:4d455c36188aba912ef3b84f32d03bf4e888b052559408f05bd62cddb4be44a0",
	"illum_angle_336.tif": "sha256:91d6ee9591e367f8bfb70f97a4db8ecd1e084d9159d0da3a139c23a859bc9e04",
	"illum_angle_348.tif": "sha256:531c4e3a30879829cc8874197464e12019b437f2374a7776686acff09edebef2",
	"illum_angle_36.tif": "sha256:28eeb3a2f87bab920ec98e391bfcc33da4a7bde0db2e70107950a87697409ed5",
	"illum_angle_360.tif": "sha256:b76a5dd0b74125fd9ac97f8ac6f66979c1bdd8c1e9eecd8d8457445580150f77",
	"illum_angle_48.tif": "sha256:d186c9d22866f63a1a3547434615d6a621299e00a99eaeb45bc0a584c1b37414",
	"illum_angle_60.tif": "sha256:b36cd2b4d8e0253e3c8cc3c3c3fe2fb86d1a8edc4f045e978a877f612d0359fe",
	"illum_angle_72.tif": "sha256:b9393b622e5d630366c69f38136256735b68af0363e138c21616f4a746b9b51e",
	"illum_angle_84.tif": "sha256:047f296aa77e0bc933dbb3370de04a0fd7f85d4c4253c370683d945405bb345b",
	"illum_angle_96.tif": "sha256:69a9e39df0d83b2bbae860eb1eedced695f203936d9e4b129a6912bf685aee0c",
	"meteor_angle_0.tif": "sha256:f0f1a479da4b163cfb46c147c40e0ba32112864c5bcd93695db963cd5199fa19",
	"meteor_angle_108.tif": "sha256:57f9f5c8045d05f056ff9394200260f19fa70c8e1af7e58f94b96fc375e771f7",
	"meteor_angle_12.tif": "sha256:35130d734545c1b7f9b471981bd8b626805191b544af0f535411aa2a43584200",
	"meteor_angle_120.tif": "sha256:15a2fc72f67c4e8fb45e540e64a6b42c3e927e2cc04962c36020b1190694a800",
	"meteor_angle_132.tif": "sha256:e3ce7ccc15e81c0106f96df9a07b8201f1b2fd00f007e595b286de43b51eac1b",
	"meteor_angle_144.tif": "sha256:1cdad2669f6a895b6e58b9b395b74cdccd8498820b77ecf8527fe2342521cc24",
	"meteor_angle_156.tif": "sha256:d32a6c923d22e30b084ef1a36f55b016246726e52983726c9113a915801493d6",
	"meteor_angle_168.tif": "sha256:4ae9d89a6f64b86339c5bd781bf90d61cf0d8213298c985da359af4bd34ea2c5",
	"meteor_angle_180.tif": "sha256:f8d9578936cd590a8673d2588f0d89a7e3ac01ee5fd30e59aa1a565bfa92e499",
	"meteor_angle_192.tif": "sha256:8b5e1be3f79184761b37d1cb1d99a0dd85a83ac3c91ee33df1bc9a5a7cbc8eba",
	"meteor_angle_204.tif": "sha256:4c3219beb74e1ca7547e78d26960cd72578e79a536bc5403480491ea7524dd33",
	"meteor_angle_216.tif": "sha256:a4bdf811db4c17bab9f6f1b112e08aa1519457d39359474e7243d581c792795a",
	"meteor_angle_228.tif": "sha256:95decbd191bc1e59b1145cf287661041dbe17a6f5b4c0c97b8d1a14340d1ef92",
	"meteor_angle_24.tif": "sha256:28eeb3a2f87bab920ec98e391bfcc33da4a7bde0db2e70107950a87697409ed5",
	"meteor_angle_240.tif": "sha256:790f7bffaf32011a8923f22d05c3f0688fc06f600e08fc9b02c19687f03ce566",
	"meteor_angle_252.tif": "sha256:536a90a7048130326c9614ed35d238164b448460af8ad030dcbb657728000b94",
	"meteor_angle_264.tif": "sha256:4466bfd4e73126b3fc7b945844122f475ffca40c11ae70e31fb89f29ceedd02a",
	"meteor_angle_276.tif": "sha256:bdee3d16512109206e80cec2a54246a12ff832313e750979a2e4deb9370ce3f6",
	"meteor_angle_288.tif": "sha256:18308fccd5c315acc3271e65f7cef740b669a899c9ca2ad6150db81ca732fdf6",
	"meteor_angle_300.tif": "sha256:0adc32a6be9fb79b3bf76d4403211e10d971d8229535a02f49d0d3fcc7f2e879",
	"meteor_angle_312.tif": "sha256:4d455c36188aba912ef3b84f32d03bf4e888b052559408f05bd62cddb4be44a0",
	"meteor_angle_324.tif": "sha256:91d6ee9591e367f8bfb70f97a4db8ecd1e084d9159d0da3a139c23a859bc9e04",
	"meteor_angle_336.tif": "sha256:531c4e3a30879829cc8874197464e12019b437f2374a7776686acff09edebef2",
	"meteor_angle_348.tif": "sha256:b76a5dd0b74125fd9ac97f8ac6f66979c1bdd8c1e9eecd8d8457445580150f77",
	"meteor_angle_36.tif": "sha256:d186c9d22866f63a1a3547434615d6a621299e00a99eaeb45bc0a584c1b37414",
	"meteor_angle_48.tif": "sha256:b36cd2b4d8e0253e3c8cc3c3c3fe2fb86d1a8edc4f045e978a877f612d0359fe",
	"meteor_angle_60.tif": "sha256:b9393b622e5d630366c69f38136256735b68af0363e138c21616f4a746b9b51e",
	"meteor_angle_72.tif": "sha256:047f296aa77e0bc933dbb3370de04a0fd7f85d4c4253c370683d945405bb345b",
	"meteor_angle_84.tif": "sha256:69a9e39df0d83b2bbae860eb1eedced695f203936d9e4b129a6912bf685aee0c",
	"meteor_angle_96.tif": "sha256:65bd435c3bbbbd9686fd1943c068d987c66a349fd6240c6babc4aa61d1a15cad",
	"meteor_flux.tif": "sha256:972ea361c22d84ca34a4ccd411241d310a83dbaa9172b32385e3491b81035fa2",
	"moon_de440_250416.tf": "sha256:a47c71e9c9f33796bdafb2c9d69a7ee447b6016ecad80f71cd6f3e479f9cf768",
	"moon_pa_de440_200625.bpc": "sha256:60cd55aa401ea2ea97360636f567554bfe4e37bb829f901b4460a455dfaf783f",
	"naif0012.tls": "sha256:678e32bdb5a744117a467cd9601cd6b373f0e9bc9bbde1371d5eee39600a039b",
	"pck00011.tpc": "sha256:3dff7b1dbeceaa01f25467767d3fa25816051c85d162d1edf04acb310ee28bb1",
	"polar_south_80_summer_avg-float.tif": "sha256:0be252e5fbaec7a12adf2e7ea04f2ade0ceefb3a6995f6ac68157e3a87d0b6b0",
	"polar_south_80_summer_max-float.tif": "sha256:ba4a1b6275402d6b0c1000ceb0208ad63d37665afaeb902ab6f108c67c0a0c67",
	"polar_south_80_summer_min-float.tif": "sha256:793d4a83c111b8a603f7b726ce5f7efae02e21e19f2589595922b348286d7721",
	"polar_south_80_winter_avg-float.tif": "sha256:5f1fb5149a426d5749938111b57f5710b0522e874c8cad6ba36fca23682e6f85",
	"polar_south_80_winter_max-float.tif": "sha256:d61e264e1179fdcf8df7d471798b5f47bb80f59c13ec2088cd3913e72c001282",
	"polar_south_80_winter_min-float.tif": "sha256:d12fd9becb91bc7d65a49729049381718fecff55784473c3d6664a60b4d96607",
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
