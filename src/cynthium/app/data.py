import os
from pathlib import Path

import pooch
import requests

GITHUB_URL = os.environ.get(
	"CYNTHIUM_DATA_BASE_URL",
	"https://github.com/osh3276/cynthium/releases/download/data-v1.0.0b2/",
)

REGISTRY = {
"DM1_5mpp_surf.tif": "sha256:ceb7e786d05ef6a604c80b78be885e641ad7bd2b5c3aac944201a4f2008d8ca4",
	"DM1_final_adj_5mpp_slp.tif": "sha256:0b781ed17ce8d4dab1063bfa1a5c4f1efba41fd1ec95206f1c728d84ada0c577",
	"DM2_5mpp_surf.tif": "sha256:d88677c21633683061117db0a577f0510e0948fe9db315d13be28782407ff604",
	"DM2_final_adj_5mpp_slp.tif": "sha256:dc62edf86ae6717eb37aeaf4f9c8fb65e8d3833be7716461fa184012888c7254",
	"Haworth_5mpp_surf.tif": "sha256:387fd6e99bca266f4982f7256c4c185921105313882b4c2eee5b5ff1ef75016b",
	"Haworth_final_adj_5mpp_slp.tif": "sha256:e6126acd792247b17109aaa57a0bed941afc37995cc72cc2f26b7a229f1e38de",
	"Illumination_mask_80mpp_FULL_GEO.tif": "sha256:7181bc83ca527c4d4ab1f5b44ce187b28dbe13d4874c5879489640abdb2af456",
	"Illumination_mask_80mpp_Full_Region.tif": "sha256:86fe3d5a91ce6d6e994ee6206a6b98d96dda7e16b20d330eeaa9cd3960284c2b",
	"LM1_5mpp_surf.tif": "sha256:acdb5999fbbf1d3720cee1a5e3955db9c4575a4f3665ad8443199c0f7a1d4c0c",
	"LM1_final_adj_5mpp_slp.tif": "sha256:a48a15d6bb4b6908801c723c6b1c31157a4c266c985595ef1ecbe3461df02fb1",
	"LM2_5mpp_surf.tif": "sha256:2ae42c1da672a1273754bf04e4598695b75a7833a6948b7d2893e2dd58152716",
	"LM2_final_adj_5mpp_slp.tif": "sha256:a3d8108eb2e122156bbfac58831deae34226e6e0c5b9abbba61fc65042789757",
	"LM3_5mpp_surf.tif": "sha256:df159a1c7947394fd08217e9654651b020a3816fefbc143053c10d6ee386a548",
	"LM3_final_adj_5mpp_slp.tif": "sha256:04510d6dee9bce5a7a99fa9632feb1d8834dd3158049d6d74f429456c46d5595",
	"LM4_5mpp_surf.tif": "sha256:838eef455d71c86aa5fe1390df87772b82c9e6a812f68da027b554b521ce259d",
	"LM4_final_adj_5mpp_slp.tif": "sha256:94578253808949f903f05c87beebf0253c667df09693276b0385cc21807237b9",
	"LM5_5mpp_surf.tif": "sha256:611eb3b0d59570fbafd25ffae4bdbf40603e958a740654233834848d7fb14ad5",
	"LM5_final_adj_5mpp_slp.tif": "sha256:92f9e7b38f100e7a09cdf4cd38b60eacde8102c31062fca585d3579a17d20fd7",
	"LM6_5mpp_surf.tif": "sha256:452d0137122a787edff4e0ae7baeaac2b795d14cb48b3b8c0308be1aa6c44778",
	"LM6_final_adj_5mpp_slp.tif": "sha256:09236004dc89aa3b5febc127dc8cfbe4230431ea05cc622cfcf9066935bc7ae5",
	"LM7_5mpp_surf.tif": "sha256:00930f9d110d5477b6d38349eb544ec35d0bb802035113a0894479c317d29023",
	"LM7_final_adj_5mpp_slp.tif": "sha256:e226aa0fb106c1a1fbd938b072047cb85d7dd74ae1974a93c47b9758ca800949",
	"LM8_5mpp_surf.tif": "sha256:53a4ec1c2513f3bcd59d81b9afa04174f6283cb2cd29a3bba9a33e4b9a40c979",
	"LM8_final_adj_5mpp_slp.tif": "sha256:5257d0cffa9b10bf742d20d8e6c61f9c8ef653568b685ca9dd0585b228a608d2",
	"NPA_5mpp_surf.tif": "sha256:1d13a8befcaefbe168589d525aee05a14aff222068221d93406ce951600d2b32",
	"NPA_final_adj_5mpp_slp.tif": "sha256:39bbbfee6386fe2c87abe010e24e66b46b5017a5e1f5d9d0a4b4718a2abb87af",
	"NPB_5mpp_surf.tif": "sha256:43e250222a3dd0aeee24b3a8a3fcb2303f5c51ad5655cc41590c95b929b342b8",
	"NPB_final_adj_5mpp_slp.tif": "sha256:c225fca45ecad965df01b5f486d6377ab293f07a72611614a5a1a9c4609c04a4",
	"NPC_5mpp_surf.tif": "sha256:af952c0d255d815c87e4f5521bff98ef22f3570853a1995008e70c7a3fec738a",
	"NPC_final_adj_5mpp_slp.tif": "sha256:6031360e2f61c653718fe1a484a7b8b37efc2e920ad136b28376b63cd84e04b7",
	"NPD_5mpp_surf.tif": "sha256:c60be0a03f38dea0d250791373d8f13445c5bdbad7c49690e004f238ef309c78",
	"NPD_final_adj_5mpp_slp.tif": "sha256:61af87f1beccba777d16a6ce9552508ebfc439f12cb0c0192e18d6ab3f04b6d8",
	"SL2_5mpp_surf.tif": "sha256:16737cb5fdaa47f243715e003450deadeabc6fb1b947a5ed245d5a3fd78a2208",
	"SL2_final_adj_5mpp_slp.tif": "sha256:06d50fd00ec4d0bb00b15c6c4b8c0cff9a11afa0084c1bb4fd42e9486e815f8b",
	"SL3_final_adj_5mpp_slp.tif": "sha256:5c5a40da984acf6c6d2bff50c306b9fdd1a77f9cc7f6cff6bf83f67eda5788c9",
	"Shoemaker_5mpp_surf.tif": "sha256:75329262a6dbe37e4370adcf23ec3854396c9d3e911a682d76c170178a0b8290",
	"Shoemaker_final_adj_5mpp_slp.tif": "sha256:1d03f26f3d011da0a43b8785ea4c9b565b268b06144844809a6b3a4a07d6e81b",
	"Site01_5mpp_surf.tif": "sha256:3ba7b97cb00a2bcf21189c3aeb535f65afc21207154ab9f0d43c5bdc1f7e747e",
	"Site01_final_adj_5mpp_slp.tif": "sha256:3a90035a4946b4a04b7332c52f0b2b1cff71648bd8c105e14d8a7e15c6bcfe8e",
	"Site04_5mpp_surf.tif": "sha256:38ff70dbdf2f066c2cfa94a646c3a59d653ce7f6b4528b15fc1b43ee397ce758",
	"Site04_final_adj_5mpp_slp.tif": "sha256:ec3cfa184b114d95aff498e7452764a8569737ae829e7ff3efd38d5187182579",
	"Site06_5mpp_surf.tif": "sha256:cca17e8067601dd659b583f889204db6bce685bc30c60a9e62427a8bce36b03d",
	"Site06_final_adj_5mpp_slp.tif": "sha256:47db26dc18aa8f253a7d281ccf86189bb8dfd2b33b8a5b7c20586e4877c24e0c",
	"Site07_5mpp_surf.tif": "sha256:38aaee10bb4da4d63e7427aa1ca25c79bdbc649d212079a04990e135462091f8",
	"Site07_final_adj_5mpp_slp.tif": "sha256:febfe1bf19087f537bba2f7854d40ac83adadba5003f2585b1685cbd90d02219",
	"Site11_5mpp_surf.tif": "sha256:58f3372c35bbd6baf38ffd5633c1c96b59bd89dbd252150581d12893a43136e5",
	"Site11_final_adj_5mpp_slp.tif": "sha256:c7f3eca389cf323e276955ed8e77b3eb870c576f4adf6b481014a1de6a403e23",
	"Site20_5mpp_surf.tif": "sha256:e51451f3629ba7cd5cfc1b32c8c0ee3c5c454607488b00ea00cd06a9e301a892",
	"Site20_final_adj_5mpp_slp.tif": "sha256:1e3c09698e731c6ed5ed153a0a39bed79536cebf45d699d198e8fd647d1d561e",
	"Site20v2_5mpp_surf.tif": "sha256:0e96c40987c0814eadd4f94f85dacbb33bcab5388dd0b1dc99dc59bf987f072f",
	"Site20v2_final_adj_5mpp_slp.tif": "sha256:0a505d4e93642c97e171588383b5bc3170311a4c727f73bfd92fd438d87f558f",
	"Site23_5mpp_surf.tif": "sha256:12d280a59cd7580415f6bada638d0abe025ce6727541fddf68d5dc371a6c94cf",
	"Site23_final_adj_5mpp_slp.tif": "sha256:e2b41c65a9c9044d359f634e706b71fa187dbe7d9f271d5410cbd81d68eadb91",
	"Site42_5mpp_surf.tif": "sha256:5af35ddca6ee9d7b10348610cb6714fd6d04dcce08d4e8cb6fb1113f4c1839cf",
	"Site42_final_adj_5mpp_slp.tif": "sha256:11e2ffa5d1f53e8f27b2b499380f5aa2fbd6c56d9181034e8e2e241aa48822e2",
	"Summer_Illumination_mask_80mpp_SPole_GEO.tif": "sha256:e0c19ec2283779667fbba1c4eb67c6f15beb1833e4a61b0ee1312c7ac786e518",
	"Winter_Illumination_mask_80mpp_SPole_GEO.tif": "sha256:a6fec52f4d5669870ea47379d5d8e28558fbb6aad011af211949edea6353305b",
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
	"polar_south_80_summer_avg-float.tif": "sha256:0be252e5fbaec7a12adf2e7ea04f2ade0ceefb3a6995f6ac68157e3a87d0b6b0",
	"polar_south_80_summer_max-float.tif": "sha256:ba4a1b6275402d6b0c1000ceb0208ad63d37665afaeb902ab6f108c67c0a0c67",
	"polar_south_80_summer_min-float.tif": "sha256:793d4a83c111b8a603f7b726ce5f7efae02e21e19f2589595922b348286d7721",
	"polar_south_80_winter_avg-float.tif": "sha256:5f1fb5149a426d5749938111b57f5710b0522e874c8cad6ba36fca23682e6f85",
	"polar_south_80_winter_max-float.tif": "sha256:d61e264e1179fdcf8df7d471798b5f47bb80f59c13ec2088cd3913e72c001282",
	"polar_south_80_winter_min-float.tif": "sha256:d12fd9becb91bc7d65a49729049381718fecff55784473c3d6664a60b4d96607",
	"naif0012.tls": "sha256:678e32bdb5a744117a467cd9601cd6b373f0e9bc9bbde1371d5eee39600a039b",
	"de430.bsp": "sha256:6e1b277c5f07135a84950604b83e56b736be696a7f3560bcddb1d4aeb944fca1",
	"moon_pa_de440_200625.bpc": "sha256:60cd55aa401ea2ea97360636f567554bfe4e37bb829f901b4460a455dfaf783f",
	"moon_de440_250416.tf": "sha256:a47c71e9c9f33796bdafb2c9d69a7ee447b6016ecad80f71cd6f3e479f9cf768",
	"pck00011.tpc": "sha256:3dff7b1dbeceaa01f25467767d3fa25816051c85d162d1edf04acb310ee28bb1",
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
