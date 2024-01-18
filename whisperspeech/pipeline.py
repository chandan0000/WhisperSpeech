# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/7. Pipeline.ipynb.

# %% auto 0
__all__ = ['Pipeline']

# %% ../nbs/7. Pipeline.ipynb 1
import torch
from whisperspeech.t2s_up_wds_mlang_enclm import TSARTransformer
from whisperspeech.s2a_delar_mup_wds_mlang import SADelARTransformer
from whisperspeech.a2wav import Vocoder
import traceback
from pathlib import Path

# %% ../nbs/7. Pipeline.ipynb 2
class Pipeline:
    default_speaker = torch.tensor(
       [-0.2929, -0.4503,  0.4155, -0.1417,  0.0473, -0.1624, -0.2322,  0.7071,
         0.4800,  0.5496,  0.0410,  0.6236,  0.4729,  0.0587,  0.2194, -0.0466,
        -0.3036,  0.0497,  0.5028, -0.1703,  0.5039, -0.6464,  0.3857, -0.7350,
        -0.1605,  0.4808,  0.5397, -0.4851,  0.1774, -0.8712,  0.5789,  0.1785,
        -0.1417,  0.3039,  0.4232, -0.0186,  0.2685,  0.6153, -0.3103, -0.5706,
        -0.4494,  0.3394, -0.6184, -0.3617,  1.1041, -0.1178, -0.1885,  0.1997,
         0.5571, -0.2906, -0.0477, -0.4048, -0.1062,  1.4779,  0.1639, -0.3712,
        -0.1776, -0.0568, -0.6162,  0.0110, -0.0207, -0.1319, -0.3854,  0.7248,
         0.0343,  0.5724,  0.0670,  0.0486, -0.3813,  0.1738,  0.3017,  1.0502,
         0.1550,  0.5708,  0.0366,  0.5093,  0.0294, -0.7091, -0.8220, -0.1583,
        -0.2343,  0.1366,  0.7372, -0.0631,  0.1505,  0.4600, -0.1252, -0.5245,
         0.7523, -0.0386, -0.2587,  1.0066, -0.2037,  0.1617, -0.3800,  0.2790,
         0.0184, -0.5111, -0.7291,  0.1627,  0.2367, -0.0192,  0.4822, -0.4458,
         0.1457, -0.5884,  0.1909,  0.2563, -0.2035, -0.0377,  0.7771,  0.2139,
         0.3801,  0.6047, -0.6043, -0.2563, -0.0726,  0.3856,  0.3217,  0.0823,
        -0.1302,  0.3287,  0.5693,  0.2453,  0.8231,  0.0072,  1.0327,  0.6065,
        -0.0620, -0.5572,  0.5220,  0.2485,  0.1520,  0.0222, -0.2179, -0.7392,
        -0.3855,  0.1822,  0.1042,  0.7133,  0.3583,  0.0606, -0.0424, -0.9189,
        -0.4882, -0.5480, -0.5719, -0.1660, -0.3439, -0.5814, -0.2542,  0.0197,
         0.4942,  0.0915, -0.0420, -0.0035,  0.5578,  0.1051, -0.0891,  0.2348,
         0.6876, -0.6685,  0.8215, -0.3692, -0.3150, -0.0462, -0.6806, -0.2661,
        -0.0308, -0.0050,  0.6756, -0.1647,  1.0734,  0.0049,  0.4969,  0.0259,
        -0.8949,  0.0731,  0.0886,  0.3442, -0.1433, -0.6804,  0.2204,  0.1859,
         0.2702,  0.1699, -0.1443, -0.9614,  0.3261,  0.1718,  0.3545, -0.0686]
    )
    
    def __init__(self, t2s_ref=None, s2a_ref=None, optimize=True, torch_compile=False):
        args = dict()
        try:
            if t2s_ref:
                args["ref"] = t2s_ref
            self.t2s = TSARTransformer.load_model(**args).cuda()
            if optimize: self.t2s.optimize(torch_compile=torch_compile)
        except:
            print("Failed to load the T2S model:")
            print(traceback.format_exc())
        try:
            if s2a_ref:
                args["ref"] = s2a_ref
            self.s2a = SADelARTransformer.load_model(**args).cuda()
            if optimize: self.s2a.optimize(torch_compile=torch_compile)
        except:
            print("Failed to load the S2A model:")
            print(traceback.format_exc())
        self.vocoder = Vocoder()
        self.encoder = None

    def extract_spk_emb(self, fname):
        """Extracts a speaker embedding from the first 30 seconds of the give audio file.
        """
        import torchaudio
        if self.encoder is None:
            from speechbrain.pretrained import EncoderClassifier
            self.encoder = EncoderClassifier.from_hparams("speechbrain/spkrec-ecapa-voxceleb",
                                                          savedir="~/.cache/speechbrain/",
                                                          run_opts={"device": "cuda"})
        samples, sr = torchaudio.load(fname)
        samples = self.encoder.audio_normalizer(samples[0,:30*sr], sr)
        spk_emb = self.encoder.encode_batch(samples)
        return spk_emb[0,0]
        
    def generate_atoks(self, text, speaker=None, lang='en', cps=15, step_callback=None):
        if speaker is None: speaker = self.default_speaker
        elif isinstance(speaker, (str, Path)): speaker = self.extract_spk_emb(speaker)
        text = text.replace("\n", " ")
        stoks = self.t2s.generate(text, cps=cps, lang=lang, step=step_callback)
        return self.s2a.generate(stoks, speaker.unsqueeze(0), step=step_callback)
        
    def generate(self, text, speaker=None, lang='en', cps=15, step_callback=None):
        return self.vocoder.decode(self.generate_atoks(text, speaker, lang=lang, cps=cps, step_callback=step_callback))
    
    def generate_to_file(self, fname, text, speaker=None, lang='en', cps=15, step_callback=None):
        self.vocoder.decode_to_file(fname, self.generate_atoks(text, speaker, lang=lang, cps=cps, step_callback=None))
        
    def generate_to_notebook(self, text, speaker=None, lang='en', cps=15, step_callback=None):
        self.vocoder.decode_to_notebook(self.generate_atoks(text, speaker, lang=lang, cps=cps, step_callback=None))
