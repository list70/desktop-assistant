import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { VRMLoaderPlugin } from '@pixiv/three-vrm';

export class CharacterManager {
  constructor() {
    this.scene = null;
    this.camera = null;
    this.renderer = null;
    this.vrm = null;
    this.defaultChar = null;
    this.clock = new THREE.Clock();
    this.isBlinking = false;
  }

  async init(canvas) {
    this.renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
    this.renderer.setSize(canvas.clientWidth, canvas.clientHeight);
    this.renderer.setPixelRatio(window.devicePixelRatio);
    if (THREE.SRGBColorSpace) {
      this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    }
    
    this.scene = new THREE.Scene();
    
    this.camera = new THREE.PerspectiveCamera(30.0, canvas.clientWidth / canvas.clientHeight, 0.1, 20.0);
    this.camera.position.set(0.0, 1.1, 2.5);
    
    // Balanced lighting for anime cel-shading and standard materials
    const ambientLight = new THREE.AmbientLight(0xffffff, 1.2);
    this.scene.add(ambientLight);
    
    const hemiLight = new THREE.HemisphereLight(0xffffff, 0x444444, 0.8);
    hemiLight.position.set(0, 20, 0);
    this.scene.add(hemiLight);
    
    const dirLightFront = new THREE.DirectionalLight(0xffffff, 1.2);
    dirLightFront.position.set(0.0, 1.0, 2.0);
    this.scene.add(dirLightFront);

    const dirLightBack = new THREE.DirectionalLight(0xaaccff, 0.5);
    dirLightBack.position.set(0.0, 1.0, -2.0);
    this.scene.add(dirLightBack);

    window.addEventListener('resize', () => {
      this.camera.aspect = canvas.clientWidth / canvas.clientHeight;
      this.camera.updateProjectionMatrix();
      this.renderer.setSize(canvas.clientWidth, canvas.clientHeight);
    });

    // Try to load AURA VRM model, fall back to default
    try {
      await this.loadVRM('../assets/models/aura.vrm');
      console.log('AURA model loaded successfully');
    } catch (e) {
      console.log('Model load failed, using default character:', e);
      this.loadDefaultCharacter();
    }
    
    this.animate();
    this.playBlinkAnimation();
  }

  async loadVRM(path) {
    const loader = new GLTFLoader();
    loader.register((parser) => new VRMLoaderPlugin(parser));

    try {
      const gltf = await loader.loadAsync(path);
      if (this.vrm) this.scene.remove(this.vrm.scene);
      if (this.defaultChar) {
        this.scene.remove(this.defaultChar);
        this.defaultChar = null;
      }
      
      this.vrm = gltf.userData.vrm;
      if (this.vrm && this.vrm.scene) {
        this.scene.add(this.vrm.scene);
        this.vrm.scene.rotation.y = Math.PI;
      } else if (gltf.scene) {
        this.scene.add(gltf.scene);
        gltf.scene.rotation.y = Math.PI;
      }
    } catch (e) {
      console.error('Failed to load VRM:', e);
      throw e;
    }
  }

  loadDefaultCharacter() {
    if (this.defaultChar) this.scene.remove(this.defaultChar);
    
    this.defaultChar = new THREE.Group();
    
    // Head
    const headGeo = new THREE.SphereGeometry(0.2, 32, 32);
    const headMat = new THREE.MeshLambertMaterial({ color: 0xffd1b3 });
    const head = new THREE.Mesh(headGeo, headMat);
    head.position.y = 1.4;
    this.defaultChar.add(head);
    this.headMesh = head; // Keep ref for emotions
    
    // Body
    const bodyGeo = new THREE.BoxGeometry(0.3, 0.4, 0.2);
    const bodyMat = new THREE.MeshLambertMaterial({ color: 0x88ccff });
    const body = new THREE.Mesh(bodyGeo, bodyMat);
    body.position.y = 1.0;
    this.defaultChar.add(body);
    
    this.scene.add(this.defaultChar);
  }

  setEmotion(emotion) {
    if (this.vrm) {
      this.vrm.expressionManager.setValue('happy', 0);
      this.vrm.expressionManager.setValue('sad', 0);
      this.vrm.expressionManager.setValue('angry', 0);
      this.vrm.expressionManager.setValue('relaxed', 0);
      this.vrm.expressionManager.setValue('surprised', 0);
      
      if (['happy', 'sad', 'angry', 'relaxed', 'surprised'].includes(emotion)) {
        this.vrm.expressionManager.setValue(emotion, 1.0);
      }
    } else if (this.defaultChar) {
      let color = 0xffd1b3;
      if (emotion === 'happy') color = 0xffffcc;
      else if (emotion === 'sad') color = 0xccccff;
      else if (emotion === 'thinking') color = 0xccffcc;
      else if (emotion === 'surprised') color = 0xffcccc;
      
      this.headMesh.material.color.setHex(color);
    }
  }

  startLipSync(volume) {
    const mouthOpen = Math.min(volume * 5.0, 1.0);
    if (this.vrm) {
      this.vrm.expressionManager.setValue('aa', mouthOpen);
    } else if (this.defaultChar) {
      // Just a simple scale effect
      this.headMesh.scale.y = 1.0 + mouthOpen * 0.1;
    }
  }

  stopLipSync() {
    if (this.vrm) {
      this.vrm.expressionManager.setValue('aa', 0);
    } else if (this.defaultChar) {
      this.headMesh.scale.y = 1.0;
    }
  }

  playIdleAnimation(delta) {
    const time = this.clock.getElapsedTime();
    const sway = Math.sin(time) * 0.02;
    
    if (this.vrm) {
      this.vrm.scene.position.y = sway;
    } else if (this.defaultChar) {
      this.defaultChar.position.y = sway;
    }
  }

  playBlinkAnimation() {
    const loop = () => {
      const delay = 3000 + Math.random() * 3000;
      setTimeout(() => {
        if (this.vrm) {
          this.vrm.expressionManager.setValue('blink', 1.0);
          setTimeout(() => {
            if (this.vrm) this.vrm.expressionManager.setValue('blink', 0.0);
            loop();
          }, 150);
        } else {
          loop();
        }
      }, delay);
    };
    loop();
  }

  animate() {
    requestAnimationFrame(() => this.animate());
    const delta = this.clock.getDelta();
    
    if (this.vrm) {
      this.vrm.update(delta);
    }
    
    this.playIdleAnimation(delta);
    this.renderer.render(this.scene, this.camera);
  }

  dispose() {
    this.renderer.dispose();
  }
}
